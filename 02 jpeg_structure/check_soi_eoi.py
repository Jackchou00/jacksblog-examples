# This is a JPEG/JFIF parser, only checks for SOI and EOI markers by byte patterns using stack.
# Not robust, only for demonstration.

import os
from typing import List, Tuple, Dict, Any

# Define JPEG/JFIF markers
SOI_MARKER = b"\xff\xd8"
EOI_MARKER = b"\xff\xd9"


def find_all_markers(data: bytes, marker: bytes) -> List[int]:
    """
    Tool Function:
    Find all occurrences of a marker in the data and return their positions.
    """
    positions = []
    pos = data.find(marker, 0)
    while pos != -1:
        positions.append(pos)
        pos = data.find(marker, pos + 1)
    return positions


def extract_jpeg_streams(file_path: str):
    """
    Extract, identify, and save all JPEG components from a file containing multiple JPEG streams.
    """
    try:
        with open(file_path, "rb") as f:
            data = f.read()
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        return

    soi_positions = find_all_markers(data, SOI_MARKER)
    eoi_positions = find_all_markers(data, EOI_MARKER)

    if not soi_positions or not eoi_positions:
        print("Error: No SOI or EOI markers found in the file.")
        return

    if len(soi_positions) != len(eoi_positions):
        print(
            f"Warning: Mismatch in the number of SOI markers ({len(soi_positions)}) and EOI markers ({len(eoi_positions)}). Processing may be incorrect."
        )

    events = sorted(
        [(pos, "SOI") for pos in soi_positions]
        + [(pos, "EOI") for pos in eoi_positions]
    )

    soi_stack = []
    streams_ranges = []
    for pos, type in events:
        if type == "SOI":
            soi_stack.append(pos)
        elif type == "EOI":
            if soi_stack:
                start_pos = soi_stack.pop()
                end_pos = pos + len(EOI_MARKER)
                streams_ranges.append((start_pos, end_pos))

    if not streams_ranges:
        print("Error: No valid JPEG streams found.")
        return

    # Extract all JPEG streams from the identified ranges
    all_streams = []
    for i, (start, end) in enumerate(streams_ranges):
        stream_data = data[start:end]
        all_streams.append(
            {
                "id": i,
                "start_offset": start,
                "end_offset": end,
                "size_bytes": len(stream_data),
                "data": stream_data,
                "role": "Unknown",
                "is_nested": False,
            }
        )

    # Identify nested streams (thumbnails) by checking if a stream is fully contained within another
    for i, s_inner in enumerate(all_streams):
        for j, s_outer in enumerate(all_streams):
            if i == j:
                continue
            if (
                s_inner["start_offset"] > s_outer["start_offset"]
                and s_inner["end_offset"] < s_outer["end_offset"]
            ):
                s_inner["is_nested"] = True
                s_inner["role"] = "Thumbnail"
                break

    thumbnails = [s for s in all_streams if s["is_nested"]]
    non_nested_streams = [s for s in all_streams if not s["is_nested"]]

    # First non-nested image is main image, others are auxiliary images
    main_image = None
    auxiliary_images = []

    if non_nested_streams:
        main_image = non_nested_streams[0]
        main_image["role"] = "Main Image"
        for stream in non_nested_streams[1:]:
            stream["role"] = "Auxiliary Image"
            auxiliary_images.append(stream)

    identified_streams = (
        ([main_image] if main_image else []) + thumbnails + auxiliary_images
    )
    identified_streams.sort(key=lambda x: x["start_offset"])

    for stream in identified_streams:
        print(
            f"Role: {stream['role']:<16} | "
            f"Size: {stream['size_bytes']/1024:7.2f} KB | "
            f"Offset: {stream['start_offset']} -> {stream['end_offset']}"
        )

    output_dir = "output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")

    base_name = os.path.splitext(os.path.basename(file_path))[0]

    if main_image:
        path = os.path.join(output_dir, f"{base_name}_main.jpg")
        with open(path, "wb") as f:
            f.write(main_image["data"])
        print(f"Main image saved to: {path}")

    if auxiliary_images:
        for i, aux in enumerate(auxiliary_images):
            path = os.path.join(output_dir, f"{base_name}_aux_{i}.jpg")
            with open(path, "wb") as f:
                f.write(aux["data"])
            print(f"Auxiliary image {i} saved to: {path}")

    if thumbnails:
        for i, thumb in enumerate(thumbnails):
            path = os.path.join(output_dir, f"{base_name}_thumb_{i}.jpg")
            with open(path, "wb") as f:
                f.write(thumb["data"])
            print(f"Thumbnail {i} saved to: {path}")


# --- Usage ---
file_to_process = "image.jpg"
extract_jpeg_streams(file_to_process)
