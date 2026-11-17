#!/usr/bin/env python3
"""
Streamlit app to compress scanned PDFs with OCRmyPDF
using: ocrmypdf --optimize 2 --skip-text
"""

import subprocess
import tempfile
from pathlib import Path

import streamlit as st


def compress_pdf(input_path: Path, output_path: Path) -> tuple[bool, str]:
    """Run OCRmyPDF with the requested optimization settings."""
    cmd = [
        "ocrmypdf",
        "--optimize", "2",
        "--skip-text",
        str(input_path),
        str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        return False, result.stderr
    return True, "Compression successful"


def main():
    st.set_page_config(
        page_title="PDF Compressor",
        page_icon="📄",
        layout="centered"
    )

    st.title("📄 PDF Compressor")
    st.markdown(
        "Compress scanned PDFs using **OCRmyPDF** "
        "(`--optimize 2 --skip-text`)"
    )

    uploaded_file = st.file_uploader(
        "Upload a scanned PDF",
        type=["pdf"],
        accept_multiple_files=False
    )

    if uploaded_file is not None:
        st.info(f"Uploaded: **{uploaded_file.name}** "
                f"({uploaded_file.size / 1024:.1f} KB)")

        if st.button("Compress PDF", type="primary"):
            with st.spinner("Compressing... this may take a while"):
                with tempfile.TemporaryDirectory() as tmpdir:
                    input_path = Path(tmpdir) / uploaded_file.name
                    output_path = Path(tmpdir) / f"{Path(uploaded_file.name).stem}_compressed.pdf"

                    # Save uploaded file
                    input_path.write_bytes(uploaded_file.getvalue())

                    success, message = compress_pdf(input_path, output_path)

                    if success:
                        original_size = input_path.stat().st_size
                        compressed_size = output_path.stat().st_size
                        reduction = (1 - compressed_size / original_size) * 100

                        st.success(
                            f"Done!  \n"
                            f"Original: {original_size / 1024:.1f} KB → "
                            f"Compressed: {compressed_size / 1024:.1f} KB "
                            f"({reduction:.1f}% smaller)"
                        )

                        st.download_button(
                            label="⬇️ Download compressed PDF",
                            data=output_path.read_bytes(),
                            file_name=output_path.name,
                            mime="application/pdf"
                        )
                    else:
                        st.error("Compression failed")
                        st.code(message, language="text")


if __name__ == "__main__":
    main()
