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
from libkubo import libkubo, c_str, c_bool, from_c_str, ffi

from ipfs_tk_generics.files import BaseFiles


class NodeFiles(BaseFiles):
    def __init__(self, node):
        self._node = node
        self._repo_path = self._node._repo_path


    def read(self, cid: str, *args, **kwargs) -> bytes:
        """
        Get bytes data from IPFS.

        Args:
            cid: The Content Identifier of the data to retrieve.
                 Note: This method only works with file content, not directories.
                 For directories, use the download() method instead.

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
            success = self.download(cid, temp_file_path)
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

    def publish(self, file_path: str, *args, **kwargs) -> str:
        return self._add(file_path)
    def _add(self, file_path: str, only_hash: bool = False, *args, **kwargs) -> str:
        """
        Add a file to IPFS.

        Args:
            file_path: Path to the file to add.

        Returns:
            str: The CID (Content Identifier) of the added file.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        repo_path = c_str(self._repo_path.encode('utf-8'))
        file_path_c = c_str(os.path.abspath(file_path).encode('utf-8'))

        try:
            cid_ptr = libkubo.AddFile(
                repo_path, file_path_c, c_bool(only_hash))
            if not cid_ptr:
                raise RuntimeError("Failed to add file to IPFS")

            # Copy the string content before freeing the pointer
            cid = from_c_str(cid_ptr)

            # Store the memory freeing operation in a separate try block
            try:
                # Free the memory allocated by C.CString in Go
                libkubo.FreeString(cid_ptr)
            except Exception as e:
                print(f"Warning: Failed to free memory: {e}")

            if not cid:
                raise RuntimeError("Failed to add file to IPFS")

            return cid
        except Exception as e:
            # Handle any exceptions during the process
            raise RuntimeError(f"Error adding file to IPFS: {e}")

    def download(self, cid: str, dest_path: str=".", **kwargs) -> bool:
        """
        Retrieve a file or directory from IPFS by its CID.

        Args:
            cid: The Content Identifier of the content to retrieve.
            dest_path: Destination path where the file or directory will be saved.
                       - For a file: The complete file path including filename.
                       - For a directory: The path where the directory and its contents
                         will be placed. All directory contents will be created inside 
                         this path.

        Returns:
            bool: True if the content was successfully retrieved, False otherwise.
        """
        try:
            dest_path = os.path.abspath(dest_path)
            repo_path = c_str(self._repo_path.encode('utf-8'))
            cid_c = c_str(cid.encode('utf-8'))
            dest_path_c = c_str(os.path.abspath(dest_path).encode('utf-8'))

            result = libkubo.Download(repo_path, cid_c, dest_path_c)

            return result == 0
        except Exception as e:
            # Handle any exceptions during the process
            raise RuntimeError(f"Error retrieving file from IPFS: {e}")

    def pin(self, cid: str, recursive: bool = True) -> bool:
        """
        Pin a CID to the local IPFS node.

        Args:
            cid: The Content Identifier to pin.
            recursive: Whether to recursively pin the object and its references.
                      Currently, only recursive pinning is supported.

        Returns:
            bool: True if the CID was successfully pinned, False otherwise.
        """
        try:
            repo_path = c_str(self._repo_path.encode('utf-8'))
            cid_c = c_str(cid.encode('utf-8'))

            result = libkubo.PinCID(repo_path, cid_c)

            return result == 0
        except Exception as e:
            # Handle any exceptions during the process
            raise RuntimeError(f"Error pinning CID: {e}")

    def unpin(self, cid: str, recursive: bool = True) -> bool:
        """
        Unpin a CID from the local IPFS node.

        Args:
            cid: The Content Identifier to unpin.
            recursive: Whether to recursively unpin the object and its references.
                      Currently, this parameter is ignored as all unpinning is recursive.

        Returns:
            bool: True if the CID was successfully unpinned, False otherwise.
        """
        try:
            repo_path = c_str(self._repo_path.encode('utf-8'))
            cid_c = c_str(cid.encode('utf-8'))

            result = libkubo.UnpinCID(repo_path, cid_c)

            return result == 0
        except Exception as e:
            # Handle any exceptions during the process
            raise RuntimeError(f"Error unpinning CID: {e}")

    def list_pins(self, *args, **kwargs) -> list[str]:
        """
        List all pinned CIDs in the local IPFS node.

        Returns:
            list[str]: A list of pinned CIDs.
        """
        try:
            repo_path = c_str(self._repo_path.encode('utf-8'))

            pins_json_ptr = libkubo.ListPins(repo_path)
            if not pins_json_ptr:
                raise RuntimeError("Failed to list pins")

            # Copy the string content before freeing the pointer
            pins_json = from_c_str(pins_json_ptr)

            # Store the memory freeing operation in a separate try block
            try:
                # Free the memory allocated by C.CString in Go
                libkubo.FreeString(pins_json_ptr)
            except Exception as e:
                print(f"Warning: Failed to free memory: {e}")

            if not pins_json:
                return []

            # Parse the JSON string into a Python list
            pins = json.loads(pins_json)
            return pins
        except Exception as e:
            # Handle any exceptions during the process
            raise RuntimeError(f"Error listing pins: {e}")

    def remove(self, cid: str) -> bool:
        """
        Remove a pinned object.

        This is an alias for unpin that makes the API more intuitive.

        Args:
            cid: The Content Identifier to remove.

        Returns:
            bool: True if the CID was successfully removed, False otherwise.
        """
        return self.unpin(cid)

    def predict_cid(self, filepath: str, *args, **kwargs):
        return self._add(filepath, only_hash=True)


    def terminate(self):
        pass
    def __del__(self):
        self.terminate()
