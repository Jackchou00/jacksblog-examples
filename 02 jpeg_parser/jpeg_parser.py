import struct
from collections import OrderedDict
import os


class JPEGParser:
    # XMP identifier in JPEG APP1 segment
    XMP_IDENTIFIER = b"http://ns.adobe.com/xap/1.0/\0"

    def __init__(self, filename):
        self.filename = filename
        self.markers = OrderedDict()
        self.image_width = 0
        self.image_height = 0
        self.xmp_data_list = (
            []
        )  # Store multiple XMP data, each with data and offset info

        # Standard JPEG marker definitions
        self.MARKERS = {
            0xFFD8: "SOI",  # Start of Image
            0xFFE0: "APP0",  # APP0 segment (JFIF)
            0xFFE1: "APP1",  # APP1 segment (Exif, XMP)
            0xFFE2: "APP2",
            0xFFE3: "APP3",
            0xFFE4: "APP4",
            0xFFE5: "APP5",
            0xFFE6: "APP6",
            0xFFE7: "APP7",
            0xFFE8: "APP8",
            0xFFE9: "APP9",
            0xFFEA: "APP10",
            0xFFEB: "APP11",
            0xFFEC: "APP12",
            0xFFED: "APP13",
            0xFFEE: "APP14",
            0xFFEF: "APP15",
            0xFFDB: "DQT",  # Quantization Table
            0xFFDD: "DRI",  # Define Restart Interval
            0xFFC0: "SOF0",  # Start of Frame (Baseline DCT)
            0xFFC2: "SOF2",  # Start of Frame (Progressive DCT)
            0xFFC4: "DHT",  # Huffman Table
            0xFFDA: "SOS",  # Start of Scan
            0xFFD9: "EOI",  # End of Image
        }

    def parse(self):
        """Parse JPEG file, check markers, and extract specific info"""
        try:
            with open(self.filename, "rb") as f:
                data = f.read()
        except IOError as e:
            print(f"Error: Cannot read file '{self.filename}': {e}")
            return False

        file_size = len(data)
        i = 0

        # 1. Check and record SOI (Start of Image)
        if i + 2 > file_size or data[i : i + 2] != b"\xff\xd8":
            print("Error: File is not a valid JPEG (missing SOI marker).")
            return False

        self.markers[i] = {
            "name": "SOI",
            "code": 0xFFD8,
            "length": 0,
            "offset": i,
            "info": "Start of Image",
        }
        i += 2

        # 2. Loop to parse all segments
        while i < file_size - 1:
            # Find next marker start (0xFF)
            if data[i] != 0xFF:
                # This should not happen between segments, but skip for robustness
                i += 1
                continue

            # Marker followed by 0x00 means it's a stuffed FF byte, not a marker
            if data[i + 1] == 0x00:
                i += 1
                continue

            marker_code = (data[i] << 8) | data[i + 1]
            marker_name = self.MARKERS.get(marker_code)

            # Skip unknown markers
            if marker_name is None:
                i += 1
                continue

            # Handle markers without length (e.g., SOI, EOI)
            if marker_code == 0xFFD8:  # SOI
                self.markers[i] = {
                    "name": "SOI",
                    "code": marker_code,
                    "length": 0,
                    "offset": i,
                    "info": "Start of Image",
                }
                i += 2
                continue

            if marker_code == 0xFFD9:  # EOI
                self.markers[i] = {
                    "name": "EOI",
                    "code": marker_code,
                    "length": 0,
                    "offset": i,
                    "info": "End of Image",
                }
                i += 2
                continue  # Continue parsing after EOI

            # RST markers (FFD0-FFD7) also have no length
            if 0xFFD0 <= marker_code <= 0xFFD7:
                self.markers[i] = {
                    "name": f"RST{marker_code & 0x7}",
                    "code": marker_code,
                    "length": 0,
                    "offset": i,
                    "info": "Restart Marker",
                }
                i += 2
                continue

            # Handle markers with length
            if i + 4 > file_size:
                print(
                    f"Warning: Found marker {marker_name} at offset 0x{i:06X} but file ends, cannot read length."
                )
                break

            length = struct.unpack(">H", data[i + 2 : i + 4])[0]

            # Check if declared length is valid
            if i + 2 + length > file_size:
                print(
                    f"Warning: {marker_name} segment at 0x{i:06X} declares length ({length} bytes) beyond file size."
                )
                # Record this corrupted segment, then stop parsing
                self.markers[i] = {
                    "name": marker_name,
                    "code": marker_code,
                    "length": length,
                    "offset": i,
                    "info": "Error: Segment length exceeds file!",
                }
                break

            segment_data = data[i + 4 : i + 2 + length]

            segment_info = {
                "name": marker_name,
                "code": marker_code,
                "length": length,
                "data": segment_data,
                "offset": i,
                "info": "",
            }

            # Parse content for specific segment types
            self._process_segment(segment_info)

            self.markers[i] = segment_info

            # If SOS segment, following is compressed image data until next marker
            if marker_name == "SOS":
                # Skip SOS segment header
                i += 2 + length
                # Scan image data, look for next valid marker (FF not followed by 00)
                while i < file_size - 1:
                    if data[i] == 0xFF:
                        next_byte = data[i + 1]
                        # Stuffed byte (FF 00), skip
                        if next_byte == 0x00:
                            i += 2
                            continue
                        # Restart marker (FF D0-D7), skip
                        elif 0xD0 <= next_byte <= 0xD7:
                            i += 2
                            continue
                        # Found real marker, break image data scan
                        else:
                            break
                    else:
                        i += 1
                # Now i points to next marker, main loop will handle it
            else:
                # Move to next segment
                i += 2 + length

        return True

    def _process_segment(self, segment):
        """Dispatch to specific parser based on segment type"""
        if segment["name"] == "SOF0":
            self._parse_sof0(segment)
        elif segment["name"] == "APP1":
            self._parse_app1(segment)
        elif segment["name"] == "DRI":
            self._parse_dri(segment)
        # Add more segment parsers as needed, e.g., DQT, DHT, etc.

    def _parse_sof0(self, segment):
        """Parse SOF0 segment to get image dimensions"""
        data = segment["data"]
        if len(data) >= 5:
            # Precision, height, width
            self.image_height = struct.unpack(">H", data[1:3])[0]
            self.image_width = struct.unpack(">H", data[3:5])[0]
            segment["info"] = f"Dimensions: {self.image_width}x{self.image_height}"

    def _parse_app1(self, segment):
        """Parse APP1 segment, check for XMP data"""
        data = segment["data"]
        if data.startswith(self.XMP_IDENTIFIER):
            # Found XMP data
            segment["info"] = "Contains XMP metadata"
            # Extract pure XML data (after identifier)
            xmp_content = data[len(self.XMP_IDENTIFIER) :]
            # Add XMP data and its offset info to the list
            self.xmp_data_list.append(
                {
                    "data": xmp_content,
                    "offset": segment["offset"],
                    "index": len(self.xmp_data_list),  # For unique filename
                }
            )

    def _parse_dri(self, segment):
        """Parse DRI segment to get restart interval"""
        data = segment["data"]
        if len(data) >= 2:
            # DRI segment contains a 16-bit restart interval value
            restart_interval = struct.unpack(">H", data[0:2])[0]
            segment["info"] = f"Restart Interval: {restart_interval} MCU"
        else:
            segment["info"] = "Incomplete DRI segment data"

    def print_report(self):
        """Print parsing report to console"""
        print("=" * 70)
        print(f"JPEG File Analysis Report: {self.filename}")
        print("=" * 70)

        if self.xmp_data_list:
            print(f"\nFound {len(self.xmp_data_list)} XMP metadata segment(s):")
            for i, xmp_info in enumerate(self.xmp_data_list):
                print(
                    f"  XMP #{i+1}: Offset 0x{xmp_info['offset']:06X}, Size {len(xmp_info['data'])} bytes"
                )

        print("\nJPEG Segment Analysis:")
        print(
            f"{'Offset':<10} {'Marker':<6} {'Code':<10} {'Length':<10} {'Description'}"
        )
        print("-" * 70)

        for offset, segment in self.markers.items():
            offset_hex = f"0x{offset:06X}"
            code_hex = f"0x{segment['code']:04X}"
            print(
                f"{offset_hex:<10} {segment['name']:<6} {code_hex:<10} {segment['length']:<10} {segment['info']}"
            )

        print("=" * 70)

    def save_xmp_to_file(self):
        """If XMP data is parsed, save each XMP data to a separate file"""
        if self.xmp_data_list:
            base_filename = os.path.splitext(self.filename)[0]
            saved_count = 0

            for xmp_info in self.xmp_data_list:
                # Generate unique filename with index and offset info
                if len(self.xmp_data_list) == 1:
                    # If only one XMP, use simple naming
                    output_filename = base_filename + ".xml"
                else:
                    # If multiple XMPs, use indexed and offset naming
                    output_filename = f"{base_filename}_xmp_{xmp_info['index']:02d}_0x{xmp_info['offset']:06X}.xml"

                try:
                    with open(output_filename, "wb") as f:
                        f.write(xmp_info["data"])
                    print(
                        f"Successfully extracted and saved XMP metadata to: {output_filename}"
                    )
                    saved_count += 1
                except IOError as e:
                    print(
                        f"Error: Cannot write XMP data to file '{output_filename}': {e}"
                    )

            if saved_count > 0:
                print(f"\nTotal {saved_count} XMP file(s) saved.")
        else:
            print("\nNo XMP metadata found in the file.")


def main():
    filename = "image.jpg"
    parser = JPEGParser(filename)

    if parser.parse():
        parser.print_report()
        parser.save_xmp_to_file()
    else:
        print("\nFile parsing failed.")


if __name__ == "__main__":
    main()
