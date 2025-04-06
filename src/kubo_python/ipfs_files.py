import os
import tempfile
import ctypes
import shutil
import platform
import json
import time
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union, List, Dict, Any, Callable, Tuple, Iterator, Set

class NodeFiles:

    def add_bytes(self, data: bytes, filename: Optional[str] = None) -> str:
        """
        Add bytes data to IPFS.

        Args:
            data: Bytes to add to IPFS.
            filename: Optional filename to use as a temporary file.

        Returns:
            str: The CID of the added data.
        """
        # Create a temporary file
        temp_file = None
        temp_file_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=filename if filename else '') as temp_file:
                temp_file.write(data)
                temp_file_path = temp_file.name

            # Add the temporary file to IPFS
            return self.add_file(temp_file_path)
        except Exception as e:
            raise RuntimeError(f"Error adding bytes to IPFS: {e}")
        finally:
            # Clean up the temporary file
            if temp_file_path is not None and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except Exception:
                    # Silently ignore cleanup errors
                    pass

    def add_str(self, content: str, filename: Optional[str] = None) -> str:
        """
        Add string content to IPFS.

        Args:
            content: String content to add.
            filename: Optional filename to use as a temporary file.

        Returns:
            str: The CID of the added content.
        """
        return self.add_bytes(content.encode('utf-8'), filename)

    def get_bytes(self, cid: str) -> bytes:
        """
        Get bytes data from IPFS.

        Args:
            cid: The Content Identifier of the data to retrieve.

        Returns:
            bytes: The retrieved data.
        """
        temp_file = None
        temp_file_path = None
        try:
            # Create a temporary file to store the retrieved data
            temp_file = tempfile.NamedTemporaryFile(delete=False)
            temp_file_path = temp_file.name
            temp_file.close()

            # Get the file from IPFS
            success = self.get_file(cid, temp_file_path)
            if not success:
                raise RuntimeError(f"Failed to retrieve data for CID: {cid}")

            # Read the data from the temporary file
            with open(temp_file_path, 'rb') as f:
                return f.read()
        except Exception as e:
            raise RuntimeError(f"Error retrieving bytes from IPFS: {e}")
        finally:
            # Clean up the temporary file
            if temp_file_path is not None and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except Exception:
                    # Silently ignore cleanup errors
                    pass

    def get_str(self, cid: str, encoding: str = 'utf-8') -> str:
        """
        Get string content from IPFS.

        Args:
            cid: The Content Identifier of the content to retrieve.
            encoding: The encoding to use when decoding the bytes.

        Returns:
            str: The retrieved content as a string.
        """
        data = self.get_bytes(cid)
        return data.decode(encoding)
    def add_file(self, file_path: str) -> str:
        """
        Add a file to IPFS.

        Args:
            file_path: Path to the file to add.

        Returns:
            str: The CID (Content Identifier) of the added file.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        repo_path = ctypes.c_char_p(self._repo_path.encode('utf-8'))
        file_path_c = ctypes.c_char_p(
            os.path.abspath(file_path).encode('utf-8'))

        try:
            cid_ptr = self._lib.AddFile(repo_path, file_path_c)
            if not cid_ptr:
                raise RuntimeError("Failed to add file to IPFS")

            # Copy the string content before freeing the pointer
            cid = ctypes.string_at(cid_ptr).decode('utf-8')

            # Store the memory freeing operation in a separate try block
            try:
                # Free the memory allocated by C.CString in Go
                print("FreeStr: Add File")
                self._lib.FreeString(cid_ptr)
            except Exception as e:
                print(f"Warning: Failed to free memory: {e}")

            if not cid:
                raise RuntimeError("Failed to add file to IPFS")

            return cid
        except Exception as e:
            # Handle any exceptions during the process
            raise RuntimeError(f"Error adding file to IPFS: {e}")

    def add_directory(self, dir_path: str) -> str:
        """
        Add a directory to IPFS.

        Args:
            dir_path: Path to the directory to add.

        Returns:
            str: The CID (Content Identifier) of the added directory.
        """
        if not os.path.isdir(dir_path):
            raise NotADirectoryError(f"Not a directory: {dir_path}")

        # The underlying Go implementation handles directories
        return self.add_file(dir_path)

    def get_file(self, cid: str, dest_path: str) -> bool:
        """
        Retrieve a file from IPFS by its CID.

        Args:
            cid: The Content Identifier of the file to retrieve.
            dest_path: Destination path where the file will be saved.

        Returns:
            bool: True if the file was successfully retrieved, False otherwise.
        """
        try:
            repo_path = ctypes.c_char_p(self._repo_path.encode('utf-8'))
            cid_c = ctypes.c_char_p(cid.encode('utf-8'))
            dest_path_c = ctypes.c_char_p(
                os.path.abspath(dest_path).encode('utf-8'))

            result = self._lib.GetFile(repo_path, cid_c, dest_path_c)

            return result == 0
        except Exception as e:
            # Handle any exceptions during the process
            raise RuntimeError(f"Error retrieving file from IPFS: {e}")
