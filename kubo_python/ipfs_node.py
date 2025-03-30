import os
import tempfile
import ctypes
import shutil
import platform
from pathlib import Path
from typing import Optional, Union, List, Dict, Any

class IPFSNode:
    """
    Python wrapper for a Kubo IPFS node.
    
    This class provides an interface to work with IPFS functionality
    through the Kubo implementation.
    """
    
    def __init__(self, repo_path: Optional[str] = None, online: bool = True):
        """
        Initialize an IPFS node with a specific repository path.
        
        Args:
            repo_path: Path to the IPFS repository. If None, a temporary
                       repository will be created.
            online: Whether the node should connect to the IPFS network.
        """
        self._temp_dir = None
        self._lib = None
        self._repo_path = repo_path
        self._online = online
        
        # If no repo path is provided, create a temporary directory
        if self._repo_path is None:
            self._temp_dir = tempfile.TemporaryDirectory()
            self._repo_path = self._temp_dir.name
        
        # Load the shared library
        self._load_library()
        
        # Initialize the repository if it doesn't exist
        if not os.path.exists(os.path.join(self._repo_path, "config")):
            self._init_repo()
    
    def _load_library(self):
        """Load the Kubo shared library."""
        # Determine library name based on platform
        if platform.system() == 'Windows':
            lib_name = 'libkubo.dll'
        elif platform.system() == 'Darwin':
            lib_name = 'libkubo.dylib'
        else:
            lib_name = 'libkubo.so'
        
        # Get the absolute path to the library
        lib_path = Path(__file__).parent / 'lib' / lib_name
        
        # Load the library
        try:
            self._lib = ctypes.CDLL(str(lib_path))
        except OSError as e:
            raise RuntimeError(f"Failed to load Kubo library: {e}")
        
        # Define function signatures
        self._lib.CreateRepo.argtypes = [ctypes.c_char_p]
        self._lib.CreateRepo.restype = ctypes.c_int
        
        self._lib.AddFile.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        self._lib.AddFile.restype = ctypes.c_char_p
        
        self._lib.GetFile.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
        self._lib.GetFile.restype = ctypes.c_int
        
        self._lib.ConnectToPeer.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        self._lib.ConnectToPeer.restype = ctypes.c_int
        
        self._lib.FreeString.argtypes = [ctypes.c_char_p]
        self._lib.FreeString.restype = None
    
    def _init_repo(self):
        """Initialize the IPFS repository."""
        repo_path = ctypes.c_char_p(self._repo_path.encode('utf-8'))
        result = self._lib.CreateRepo(repo_path)
        
        if result < 0:
            raise RuntimeError(f"Failed to initialize IPFS repository: {result}")
    
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
        file_path_c = ctypes.c_char_p(os.path.abspath(file_path).encode('utf-8'))
        
        cid_ptr = self._lib.AddFile(repo_path, file_path_c)
        cid = ctypes.string_at(cid_ptr).decode('utf-8')
        
        # Free the memory allocated by C.CString in Go
        self._lib.FreeString(cid_ptr)
        
        if not cid:
            raise RuntimeError("Failed to add file to IPFS")
        
        return cid
    
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
        repo_path = ctypes.c_char_p(self._repo_path.encode('utf-8'))
        cid_c = ctypes.c_char_p(cid.encode('utf-8'))
        dest_path_c = ctypes.c_char_p(os.path.abspath(dest_path).encode('utf-8'))
        
        result = self._lib.GetFile(repo_path, cid_c, dest_path_c)
        
        return result == 0
    
    def connect_to_peer(self, peer_addr: str) -> bool:
        """
        Connect to an IPFS peer.
        
        Args:
            peer_addr: Multiaddress of the peer to connect to.
            
        Returns:
            bool: True if successfully connected, False otherwise.
        """
        if not self._online:
            raise RuntimeError("Cannot connect to peers in offline mode")
        
        repo_path = ctypes.c_char_p(self._repo_path.encode('utf-8'))
        peer_addr_c = ctypes.c_char_p(peer_addr.encode('utf-8'))
        
        result = self._lib.ConnectToPeer(repo_path, peer_addr_c)
        
        return result == 0
    
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
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=filename if filename else '') as temp_file:
                temp_file.write(data)
                temp_file_path = temp_file.name
            
            # Add the temporary file to IPFS
            return self.add_file(temp_file_path)
        finally:
            # Clean up the temporary file
            if temp_file is not None and os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
    
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
        try:
            # Create a temporary file to store the retrieved data
            temp_file = tempfile.NamedTemporaryFile(delete=False)
            temp_file.close()
            
            # Get the file from IPFS
            success = self.get_file(cid, temp_file.name)
            if not success:
                raise RuntimeError(f"Failed to retrieve data for CID: {cid}")
            
            # Read the data from the temporary file
            with open(temp_file.name, 'rb') as f:
                return f.read()
        finally:
            # Clean up the temporary file
            if temp_file is not None and os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
    
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
    
    def close(self):
        """Close the IPFS node and clean up resources."""
        # Clean up temporary directory if one was created
        if self._temp_dir is not None:
            self._temp_dir.cleanup()
            self._temp_dir = None
        
        # Additional cleanup if needed
    
    def __enter__(self):
        """Support for context manager protocol."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up when exiting the context manager."""
        self.close()
    
    @classmethod
    def ephemeral(cls, online: bool = True):
        """
        Create an ephemeral IPFS node with a temporary repository.
        
        Args:
            online: Whether the node should connect to the IPFS network.
            
        Returns:
            IPFSNode: A new IPFS node instance with a temporary repository.
        """
        return cls(None, online)