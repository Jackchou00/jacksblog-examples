"""
Parse APP2 Maker Segment in ISO 21496-1 Gainmap.

Use sample_app2 from adobe's sample gallery as example.

Reference: ISO 21496-1 <https://www.iso.org/standard/86775.html>
"""


import struct
import json
import re


def clean_hex_string(hex_str: str) -> str:
    """Removes whitespace and newlines from a hex string."""
    return re.sub(r"[\s\n\r]", "", hex_str)


def hex_to_bytes(cleaned_hex: str) -> bytes:
    """Converts a cleaned hex string to a bytes object."""
    return bytes.fromhex(cleaned_hex)


def calculate_rational(numerator: int, denominator: int, is_signed: bool) -> float:
    """Calculates the float value from a numerator/denominator pair."""
    if denominator == 0:
        # The spec states denominators shall not be 0, but this is a safeguard.
        return (
            float("inf") if numerator > 0 else float("-inf") if numerator < 0 else 0.0
        )
    return float(numerator) / float(denominator)


def parse_gain_map_metadata(data: bytes) -> dict:
    """
    Parses the APP2 segment containing GainMapMetadata.
    The byte order is big-endian as per the spec.
    """
    if len(data) < 4:
        raise ValueError("Data is too short for APP2 marker and length.")

    # 1. Parse APP2 Marker and Length
    marker, length = struct.unpack(">HH", data[0:4])
    if marker != 0xFFE2:
        raise ValueError(f"Invalid APP2 marker. Expected 0xFFE2, got {marker:04X}.")

    expected_length = len(data) - 2
    if length != expected_length:
        print(
            f"Warning: Stated length in header ({length}) does not match actual segment size ({expected_length})."
        )

    # 2. Parse and verify URN
    urn_bytes = data[4:32]
    urn_string = urn_bytes.decode("utf-8").rstrip("\x00")
    expected_urn = "urn:iso:std:iso:ts:21496:-1"
    if urn_string != expected_urn:
        raise ValueError(f"Invalid URN. Expected '{expected_urn}', got '{urn_string}'.")

    offset = 32

    # 3. Parse GainMapMetadata structure
    parsed_data = {}

    # Version Info
    min_version, writer_version = struct.unpack_from(">HH", data, offset)
    parsed_data["version"] = {
        "minimum_version": min_version,
        "writer_version": writer_version,
    }
    offset += 4

    # Control Flags
    flags_byte = struct.unpack_from(">B", data, offset)[0]
    is_multichannel = (flags_byte >> 7) & 1
    use_base_colour_space = (flags_byte >> 6) & 1
    parsed_data["flags"] = {
        "is_multichannel": bool(is_multichannel),
        "use_base_colour_space": bool(use_base_colour_space),
        "reserved": flags_byte & 0x3F,  # The lower 6 bits
    }
    offset += 1

    # HDR Headroom
    (base_hdr_num, base_hdr_den, alt_hdr_num, alt_hdr_den) = struct.unpack_from(
        ">IIII", data, offset
    )

    parsed_data["hdr_headroom"] = {
        "baseline": {
            "numerator": base_hdr_num,
            "denominator": base_hdr_den,
            "value": calculate_rational(base_hdr_num, base_hdr_den, is_signed=False),
        },
        "alternate": {
            "numerator": alt_hdr_num,
            "denominator": alt_hdr_den,
            "value": calculate_rational(alt_hdr_num, alt_hdr_den, is_signed=False),
        },
    }
    offset += 16

    # Per-Channel Metadata
    num_channels = 3 if is_multichannel else 1
    channel_names = ["Red", "Green", "Blue"] if num_channels == 3 else ["Achromatic"]
    parsed_data["channels"] = []

    for i in range(num_channels):
        channel_data = {}
        # Format string for one GainMapChannel (40 bytes):
        # s32, u32, s32, u32, u32, u32, s32, u32, s32, u32
        channel_format = ">iIiIIiIiII"

        values = struct.unpack_from(channel_format, data, offset)

        channel_data["name"] = channel_names[i]
        channel_data["gain_map_min"] = {
            "numerator": values[0],
            "denominator": values[1],
            "value": calculate_rational(values[0], values[1], is_signed=True),
        }
        channel_data["gain_map_max"] = {
            "numerator": values[2],
            "denominator": values[3],
            "value": calculate_rational(values[2], values[3], is_signed=True),
        }
        channel_data["gamma"] = {
            "numerator": values[4],
            "denominator": values[5],
            "value": calculate_rational(values[4], values[5], is_signed=False),
        }
        channel_data["base_offset"] = {
            "numerator": values[6],
            "denominator": values[7],
            "value": calculate_rational(values[6], values[7], is_signed=True),
        }
        channel_data["alternate_offset"] = {
            "numerator": values[8],
            "denominator": values[9],
            "value": calculate_rational(values[8], values[9], is_signed=True),
        }

        parsed_data["channels"].append(channel_data)
        offset += struct.calcsize(channel_format)

    return {
        "app2_marker": f"0x{marker:04X}",
        "segment_length": length,
        "urn": urn_string,
        "metadata": parsed_data,
    }


def pretty_print_results(data: dict):
    """Prints the parsed data in a human-readable format."""
    print("--- Parsed Gain Map Metadata ---")
    print(f"APP2 Marker: {data['app2_marker']}")
    print(f"Segment Length: {data['segment_length']} bytes")
    print(f"URN: {data['urn']}")

    meta = data["metadata"]
    print("\n[Metadata]")
    print(
        f"  Version: Min={meta['version']['minimum_version']}, Writer={meta['version']['writer_version']}"
    )
    print(f"  Is Multichannel: {meta['flags']['is_multichannel']}")
    print(f"  Use Base Colour Space: {meta['flags']['use_base_colour_space']}")

    print("\n  [HDR Headroom]")
    print(
        f"    Baseline:  {meta['hdr_headroom']['baseline']['value']:.4f} ({meta['hdr_headroom']['baseline']['numerator']}/{meta['hdr_headroom']['baseline']['denominator']})"
    )
    print(
        f"    Alternate: {meta['hdr_headroom']['alternate']['value']:.4f} ({meta['hdr_headroom']['alternate']['numerator']}/{meta['hdr_headroom']['alternate']['denominator']})"
    )

    print("\n  [Channels]")
    for chan in meta["channels"]:
        print(f"    --- Channel: {chan['name']} ---")
        print(f"      Gain Map Min:     {chan['gain_map_min']['value']:.4f}")
        print(f"      Gain Map Max:     {chan['gain_map_max']['value']:.4f}")
        print(f"      Gamma:            {chan['gamma']['value']:.4f}")
        print(f"      Base Offset:      {chan['base_offset']['value']:.4f}")
        print(f"      Alternate Offset: {chan['alternate_offset']['value']:.4f}")
    print("\n--------------------------------")


def main():
    # read HEX_DATA from sample.
    with open("03 iso_21496_1/sample_app2", "r") as f:
        HEX_DATA = f.read()
    output = "03 iso_21496_1/sample_app2.json"
    try:
        # Step 1: Clean and convert the input string
        cleaned_hex = clean_hex_string(HEX_DATA)
        # print(f"\nCleaned Hex String:\n{cleaned_hex}\n")
        binary_data = hex_to_bytes(cleaned_hex)
        # Step 2: Parse the binary data
        parsed_structure = parse_gain_map_metadata(binary_data)
        # Step 3: Print the results
        pretty_print_results(parsed_structure)
        # Step 4: Save to JSON
        with open(output, "w") as f:
            json.dump(parsed_structure, f, indent=4)

        print(f"\nSuccessfully parsed metadata and saved to '{output}'")

    except (ValueError, struct.error) as e:
        print(f"\nError: Could not parse the data. Reason: {e}")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")


if __name__ == "__main__":
    main()
