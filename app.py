
#!/usr/bin/env python3
"""
PDF Compressor - Batch Edition

Compress multiple scanned PDFs or an entire folder using OCRmyPDF.
Settings: --optimize 2 --skip-text
"""

import io
import shutil
import subprocess
import tempfile
import zipfile

from pathlib import Path, PurePosixPath

import streamlit as st


# --------------------------------------------------
# PDF COMPRESSION
# --------------------------------------------------

def compress_pdf(input_path: Path, output_path: Path):
    """Run OCRmyPDF with the requested optimization settings."""

    cmd = [
        "ocrmypdf",
        "--optimize", "2",
        "--skip-text",
        str(input_path),
        str(output_path),
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode != 0:
            message = result.stderr or result.stdout
            return False, message or f"OCRmyPDF exited with code {result.returncode}"

        if not output_path.is_file():
            return False, "OCRmyPDF completed but no output PDF was created."

        return True, "Compression successful"

    except FileNotFoundError:
        return False, "OCRmyPDF was not found on the system PATH."

    except Exception as e:
        return False, str(e)


# --------------------------------------------------
# SAFE FILE NAMES
# --------------------------------------------------

def safe_relative_path(upload_name: str) -> Path:
    """
    Preserve folder structure where possible.
    Prevent uploaded filenames from escaping temporary folders.
    """

    normalized = upload_name.replace("\\", "/")
    parts = [
        part for part in PurePosixPath(normalized).parts
        if part not in ("", ".", "..", "/")
    ]

    if not parts:
        return Path("document.pdf")

    return Path(*parts)


def compressed_filename(relative_path: Path) -> Path:
    """Create a filename ending in _compressed.pdf."""

    return relative_path.with_name(
        relative_path.stem + "_compressed.pdf"
    )


# --------------------------------------------------
# MAIN APPLICATION
# --------------------------------------------------

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

    st.divider()

    # Input selection
    st.subheader("1. Select PDF input")

    upload_mode = st.radio(
        "How would you like to upload PDFs?",
        [
            "Multiple PDF files",
            "Entire folder"
        ],
        horizontal=True
    )

    if upload_mode == "Multiple PDF files":

        uploaded_files = st.file_uploader(
            "Select one or more PDF files",
            type=["pdf"],
            accept_multiple_files=True,
            key="multiple_pdf_upload"
        )

    else:

        uploaded_files = st.file_uploader(
            "Select a folder containing PDF files",
            type=["pdf"],
            accept_multiple_files="directory",
            key="folder_pdf_upload",
            help="Select a folder. PDFs in its subfolders are included."
        )

    if not uploaded_files:
        st.info("Please upload one or more PDF files to begin.")
        return

    # Display uploaded files
    total_files = len(uploaded_files)
    total_size = sum(f.size for f in uploaded_files)

    col1, col2 = st.columns(2)

    col1.metric("PDF files selected", total_files)
    col2.metric("Total upload size", f"{total_size / (1024 * 1024):.2f} MB")

    with st.expander("View uploaded files", expanded=False):
        for uploaded_file in uploaded_files:
            st.write(
                f"📄 {uploaded_file.name} "
                f"({uploaded_file.size / 1024:.1f} KB)"
            )

    st.divider()

    # Compression button
    st.subheader("2. Compress PDFs")

    if st.button(
        "🚀 Compress All PDFs",
        type="primary",
        use_container_width=True
    ):

        if not shutil.which("ocrmypdf"):
            st.error(
                "OCRmyPDF is not installed or cannot be found on the system PATH."
            )
            return

        results = []
        successful = 0
        failed = 0
        total_original = 0
        total_compressed = 0

        progress_bar = st.progress(0)
        status_text = st.empty()

        with tempfile.TemporaryDirectory() as tmpdir:

            temp_root = Path(tmpdir)
            input_dir = temp_root / "input"
            output_dir = temp_root / "output"

            input_dir.mkdir()
            output_dir.mkdir()

            for index, uploaded_file in enumerate(uploaded_files):

                relative_path = safe_relative_path(uploaded_file.name)

                input_path = (
                    input_dir / f"{index}_{relative_path}"
                )

                output_relative = compressed_filename(relative_path)

                output_path = (
                    output_dir / f"{index}_{output_relative}"
                )

                input_path.parent.mkdir(
                    parents=True,
                    exist_ok=True
                )

                output_path.parent.mkdir(
                    parents=True,
                    exist_ok=True
                )

                status_text.info(
                    f"Processing {index + 1} of {total_files}: "
                    f"{uploaded_file.name}"
                )

                try:

                    # Save uploaded PDF
                    file_data = uploaded_file.getvalue()
                    input_path.write_bytes(file_data)

                    original_size = input_path.stat().st_size
                    total_original += original_size

                    # Compress PDF
                    success, message = compress_pdf(
                        input_path,
                        output_path
                    )

                    if success:

                        compressed_data = output_path.read_bytes()
                        compressed_size = len(compressed_data)

                        total_compressed += compressed_size
                        successful += 1

                        reduction = (
                            (1 - compressed_size / original_size) * 100
                            if original_size else 0
                        )

                        results.append({
                            "name": uploaded_file.name,
                            "output_name": str(output_relative),
                            "success": True,
                            "original_size": original_size,
                            "compressed_size": compressed_size,
                            "reduction": reduction,
                            "data": compressed_data,
                            "message": message
                        })

                    else:

                        failed += 1

                        results.append({
                            "name": uploaded_file.name,
                            "output_name": str(output_relative),
                            "success": False,
                            "original_size": original_size,
                            "compressed_size": 0,
                            "reduction": 0,
                            "data": None,
                            "message": message
                        })

                except Exception as e:

                    failed += 1

                    results.append({
                        "name": uploaded_file.name,
                        "output_name": str(output_relative),
                        "success": False,
                        "original_size": 0,
                        "compressed_size": 0,
                        "reduction": 0,
                        "data": None,
                        "message": str(e)
                    })

                progress_bar.progress(
                    (index + 1) / total_files
                )

        status_text.success("Batch processing completed!")

        # ------------------------------------------
        # RESULTS SUMMARY
        # ------------------------------------------

        st.divider()
        st.subheader("3. Compression results")

        col1, col2, col3 = st.columns(3)

        col1.metric("Successful", successful)
        col2.metric("Failed", failed)

        if total_original:
            overall_reduction = (
                (1 - total_compressed / total_original) * 100
            )
        else:
            overall_reduction = 0

        col3.metric(
            "Overall size reduction",
            f"{overall_reduction:.1f}%"
        )

        st.write("### Individual file results")

        for index, result in enumerate(results):

            with st.container(border=True):

                if result["success"]:

                    st.success(f"✅ {result['name']}")

                    original_kb = result["original_size"] / 1024
                    compressed_kb = result["compressed_size"] / 1024

                    st.write(
                        f"Original: **{original_kb:.1f} KB**  \n"
                        f"Compressed: **{compressed_kb:.1f} KB**  \n"
                        f"Size reduction: **{result['reduction']:.1f}%**"
                    )

                    st.download_button(
                        label="⬇️ Download compressed PDF",
                        data=result["data"],
                        file_name=Path(result["output_name"]).name,
                        mime="application/pdf",
                        key=f"download_pdf_{index}"
                    )

                else:

                    st.error(f"❌ {result['name']}")
                    st.code(
                        result["message"],
                        language="text"
                    )

        # ------------------------------------------
        # DOWNLOAD ALL AS ZIP
        # ------------------------------------------

        successful_results = [
            r for r in results if r["success"]
        ]

        if successful_results:

            st.divider()
            st.subheader("4. Download all compressed PDFs")

            zip_buffer = io.BytesIO()
            used_names = set()

            with zipfile.ZipFile(
                zip_buffer,
                "w",
                compression=zipfile.ZIP_DEFLATED
            ) as zip_file:

                for result in successful_results:

                    archive_name = result["output_name"]
                    candidate = archive_name
                    counter = 2

                    # Avoid duplicate names in ZIP
                    while candidate in used_names:
                        path = Path(archive_name)
                        candidate = str(
                            path.with_name(
                                f"{path.stem}_{counter}{path.suffix}"
                            )
                        )
                        counter += 1

                    used_names.add(candidate)

                    zip_file.writestr(
                        candidate,
                        result["data"]
                    )

            st.download_button(
                label="📦 Download ALL compressed PDFs (ZIP)",
                data=zip_buffer.getvalue(),
                file_name="compressed_pdfs.zip",
                mime="application/zip",
                type="primary",
                use_container_width=True
            )

        else:

            st.warning("No PDFs were successfully compressed.")

        if failed:
            st.warning(
                f"{failed} file(s) failed. "
                "See the individual error messages above."
            )


# --------------------------------------------------
# RUN APPLICATION
# --------------------------------------------------

if __name__ == "__main__":
    main()
