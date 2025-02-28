#!/usr/bin/env python
from typing import Union, List

def do_tar(
    src_paths: Union[List[str], str],
    dest_path: str,
    transform_from: str = "/",
    transform_to: str = "/",
) -> str:
    import tarfile
    import uuid
    from pathlib import Path

    """
    Create a tar.gz archive from source files or directories and save it to the given destination.
    
    This function transforms provided GCS-style paths to absolute filesystem paths using the given
    `transform_from` and `transform_to` prefixes. It verifies that all source paths exist and that the 
    destination path is valid. If the destination is an existing directory, a unique tar.gz filename is 
    generated. If a file path is provided (which may not exist yet), its parent directory must exist.
    
    Parameters:
        src_paths (Union[List[str], str]):  Source path(s) of file(s) or directory/directories to be archived.
                                            Can be a single path string or a list of path strings.
        dest_path (str): Destination path where the tar.gz archive will be written. This can be either 
                         an existing directory or a file path (with the parent directory existing).
        transform_from (str): The prefix in the provided paths that will be replaced. Default is "/".
        transform_to (str): The prefix to use when converting to absolute filesystem paths. Default is "/".
    
    Returns:
        str: The output tar.gz file path, transformed back to the original GCS-style path.
    
    Raises:
        ValueError: If src_paths is empty, dest_path is None, any provided path does not begin with the expected
                    prefix, or if any source path or destination (or its parent) is invalid.
        RuntimeError: If an error occurs during the creation of the tar.gz archive.
    
    Example:
        >>> output = do_tar(
        ...     src_paths=["/file1.txt", "/dir1/file2.txt"],
        ...     dest_path="/tar_output",
        ...     transform_from="/",
        ...     transform_to="/path/to/root/"
        ... )
        >>> print(output)
        /tar_output/7f9c3f9a-2d75-4d2f-8b0a-0f0d7e6b1e3a.tar.gz
    """

    def transform_path_to_absolute(path: str) -> str:
        """Transform a GCS-style path to an absolute filesystem path."""
        if not path.startswith(transform_from):
            raise ValueError(
                f"Path '{path}' does not start with the expected prefix '{transform_from}'."
            )
        return path.replace(transform_from, transform_to, 1)

    def transform_path_from_absolute(path: str) -> str:
        """Transform an absolute filesystem path back to a GCS-style path."""
        if not path.startswith(transform_to):
            raise ValueError(
                f"Path '{path}' does not start with the expected prefix '{transform_to}'."
            )
        return path.replace(transform_to, transform_from, 1)

    # Convert single string path to a list for uniform processing
    if isinstance(src_paths, str):
        src_paths = [src_paths]
    
    # Validate src_paths and dest_path
    if not src_paths:
        raise ValueError("src_paths must not be empty.")
    if dest_path is None:
        raise ValueError("dest_path must not be None.")

    # Transform destination path
    transformed_dest_path = Path(transform_path_to_absolute(dest_path))
    
    # Transform and validate all source paths
    transformed_src_paths = []
    for src_path in src_paths:
        transformed_src_path = Path(transform_path_to_absolute(src_path))
        if not transformed_src_path.exists():
            raise ValueError(f"Source path '{src_path}' does not exist.")
        transformed_src_paths.append(transformed_src_path)

    # Validate transformed_dest_path
    if transformed_dest_path.exists():
        if not (transformed_dest_path.is_dir() or transformed_dest_path.is_file()):
            raise ValueError(f"Destination path '{dest_path}' is neither a directory nor a file.")
    else:
        if not transformed_dest_path.parent.exists():
            raise ValueError(
                f"Parent directory of destination path '{dest_path}' does not exist."
            )

    # Determine the final tar file path.
    if transformed_dest_path.exists() and transformed_dest_path.is_dir():
        # If destination is an existing directory, generate a unique tar file name.
        tar_file_name = f"{uuid.uuid4()}.tar.gz"
        transformed_dest_tar_path = transformed_dest_path / tar_file_name
    else:
        # Destination is treated as a file path.
        fn = transformed_dest_path.name
        if fn.endswith(".gz"):
            transformed_dest_tar_path = transformed_dest_path
        elif fn.endswith(".tar"):
            transformed_dest_tar_path = transformed_dest_path.with_name(fn + ".gz")
        else:
            transformed_dest_tar_path = transformed_dest_path.with_name(fn + ".tar.gz")
    
    # Informative message (could be replaced with logging.info in production code)
    print(f"Creating tar file at {transformed_dest_tar_path.absolute()} with {len(transformed_src_paths)} source(s)")
    
    # Create the tar.gz archive with exception handling.
    try:
        with tarfile.open(transformed_dest_tar_path, "w:gz") as tar:
            for src_path in transformed_src_paths:
                tar.add(src_path, arcname=src_path.name)
    except Exception as e:
        # Attempt to remove any incomplete tar file.
        if transformed_dest_tar_path.exists():
            try:
                transformed_dest_tar_path.unlink()
            except Exception as unlink_err:
                print(f"Warning: Failed to remove incomplete tar file '{transformed_dest_tar_path}': {unlink_err}")
        raise RuntimeError(f"Failed to create tar archive: {e}") from e

    # Transform the output path back to a GCS-style path and return.
    result_path = transform_path_from_absolute(str(transformed_dest_tar_path.absolute()))
    return result_path


if __name__ == "__main__":
    from globus_compute_sdk import Client

    gcc = Client()
    do_tar_fuid = gcc.register_function(do_tar)
    print(f"Tar func UUID is {do_tar_fuid}")

