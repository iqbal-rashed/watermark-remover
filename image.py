from pathlib import Path
from remover import remove_watermark
from PIL import Image

INPUT_PATH = "example/test.jpg"
OUTPUT_PATH = "example/out.jpg"


def main() -> None:
    if not INPUT_PATH:
        raise ValueError("INPUT_PATH must be set to an existing image file path.")
    if not OUTPUT_PATH:
        raise ValueError("OUTPUT_PATH must be set to a destination path.")

    input_file = Path(INPUT_PATH)
    output_file = Path(OUTPUT_PATH)

    image = Image.open(input_file)
    result_image, output_format = remove_watermark(
        image=image,
        mask_box="3655,2042,3797,2115",
    )

    result_image.save(output_file, format=output_format)


if __name__ == "__main__":
    main()