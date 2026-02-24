import sys
import os
import struct


def find_icc_profiles(data):
    """
    Search for all possible ICC profile start positions in binary data.
    Return a list of (start_offset, profile_size) tuples.
    """
    profiles = []
    target = b"acsp"
    offset = 0
    while True:
        pos = data.find(target, offset)
        if pos == -1:
            break
        # Calculate possible profile start position: signature offset in profile header is 36
        start = pos - 36
        if start >= 0 and start + 128 <= len(
            data
        ):  # At least able to read the full header
            # Read profile size (first 4 bytes in the header)
            size_bytes = data[start : start + 4]
            profile_size = struct.unpack(">I", size_bytes)[0]
            # Basic sanity check: size should at least include the header and not exceed file bounds
            if profile_size >= 128 and start + profile_size <= len(data):
                profiles.append((start, profile_size))
        offset = pos + 1  # Continue searching forward
    return profiles


def parse_icc_header(header_data):
    """
    Parse version number and profile class from the 128-byte ICC header.
    Return (version_str, class_str)
    """
    # Bytes 8-11: version number
    major = header_data[8]
    minor = (header_data[9] >> 4) & 0x0F
    bugfix = header_data[9] & 0x0F
    version_str = f"{major}.{minor}.{bugfix}"
    print(header_data[8:12])

    # Bytes 12-15: profile/device class signature
    class_sig = header_data[12:16].decode("ascii").strip()
    class_str = f"{class_sig}"
    return version_str, class_str


def main():
    if len(sys.argv) != 2:
        print("Usage: python extract_icc_beta.py <file_path>")
        sys.exit(1)

    filepath = sys.argv[1]
    if not os.path.isfile(filepath):
        print(f"Error: file '{filepath}' does not exist")
        sys.exit(1)

    with open(filepath, "rb") as f:
        data = f.read()

    profiles = find_icc_profiles(data)

    if not profiles:
        print("No valid ICC profile found.")
        return

    base_name = os.path.splitext(filepath)[0]
    for idx, (start, size) in enumerate(profiles, 1):
        icc_data = data[start : start + size]
        header = icc_data[:128]
        version_str, class_str = parse_icc_header(header)

        out_name = f"{base_name}_{idx:03d}.icc"
        with open(out_name, "wb") as f:
            f.write(icc_data)
        print(
            f"Extracted ICC profile #{idx} to '{out_name}' (offset: {start}, size: {size} bytes)"
        )
        print(f"  Type: {class_str}, Version: {version_str}")


if __name__ == "__main__":
    main()
