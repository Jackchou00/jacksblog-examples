"""
Parse ISO 21496-1 GainMapMetadata binary data.

Reference: ISO 21496-1 <https://www.iso.org/standard/86775.html>
"""

import struct


def calculate_rational(numerator: int, denominator: int) -> float:
    """Calculates the float value from a numerator/denominator pair."""
    if denominator == 0:
        return (
            float("inf") if numerator > 0 else float("-inf") if numerator < 0 else 0.0
        )
    return float(numerator) / float(denominator)


def parse_standard(data: bytes) -> dict:
    """Parse standard ISO 21496-1 format."""
    offset = 0

    # Version Info
    min_version, writer_version = struct.unpack_from(">HH", data, offset)
    offset += 4

    # Control Flags
    flags_byte = struct.unpack_from(">B", data, offset)[0]
    is_multichannel = (flags_byte >> 7) & 1
    use_base_colour_space = (flags_byte >> 6) & 1
    offset += 1

    # HDR Headroom (16 bytes)
    base_hdr_num = struct.unpack_from(">I", data, offset)[0]
    base_hdr_den = struct.unpack_from(">I", data, offset + 4)[0]
    alt_hdr_num = struct.unpack_from(">I", data, offset + 8)[0]
    alt_hdr_den = struct.unpack_from(">I", data, offset + 12)[0]
    offset += 16

    parsed_data = {
        "version": {"minimum_version": min_version, "writer_version": writer_version},
        "flags": {
            "is_multichannel": bool(is_multichannel),
            "use_base_colour_space": bool(use_base_colour_space),
            "reserved": flags_byte & 0x3F,
        },
        "hdr_headroom": {
            "baseline": {
                "numerator": base_hdr_num,
                "denominator": base_hdr_den,
                "value": calculate_rational(base_hdr_num, base_hdr_den),
            },
            "alternate": {
                "numerator": alt_hdr_num,
                "denominator": alt_hdr_den,
                "value": calculate_rational(alt_hdr_num, alt_hdr_den),
            },
        },
    }

    # Channel data
    num_channels = 3 if is_multichannel else 1
    channel_names = ["Red", "Green", "Blue"] if num_channels == 3 else ["Achromatic"]
    parsed_data["channels"] = []

    for i in range(num_channels):
        values = struct.unpack_from(">iIiIIIiIiI", data, offset)
        channel_data = {
            "name": channel_names[i],
            "gain_map_min": {
                "numerator": values[0],
                "denominator": values[1],
                "value": calculate_rational(values[0], values[1]),
            },
            "gain_map_max": {
                "numerator": values[2],
                "denominator": values[3],
                "value": calculate_rational(values[2], values[3]),
            },
            "gamma": {
                "numerator": values[4],
                "denominator": values[5],
                "value": calculate_rational(values[4], values[5]),
            },
            "base_offset": {
                "numerator": values[6],
                "denominator": values[7],
                "value": calculate_rational(values[6], values[7]),
            },
            "alternate_offset": {
                "numerator": values[8],
                "denominator": values[9],
                "value": calculate_rational(values[8], values[9]),
            },
        }
        parsed_data["channels"].append(channel_data)
        offset += 40

    return parsed_data


def main():
    input_file = "03 iso_21496_1/GMap"

    # Only Hasselblad X2D II needs False here.
    is_version_include = True

    try:
        with open(input_file, "rb") as f:
            binary_data = f.read()

        print(f"Read {len(binary_data)} bytes from '{input_file}'\n")

        if is_version_include:
            print(f"first byte (tmap version marker): 0x{binary_data[0]:02X}\n")
            binary_data = binary_data[1:]
            parsed = parse_standard(binary_data)
        else:
            parsed = parse_standard(binary_data)

        print(parsed)

    except FileNotFoundError:
        print(f"Error: File '{input_file}' not found")
    except struct.error as e:
        print(f"Error: Could not parse data. Reason: {e}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
