#!/usr/bin/env python3
"""
Generate checksums for EyesOff release files.
This script is used during the release process to create checksum files
that can be uploaded to GitHub alongside the release assets.
"""

import os
import sys
import hashlib
import argparse
from typing import List, Optional


def calculate_checksum(file_path: str) -> str:
    """
    Calculate SHA-256 checksum for a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        SHA-256 checksum as a hex string
    """
    hash_sha256 = hashlib.sha256()
    
    with open(file_path, 'rb') as f:
        # Read and update hash in chunks to handle large files
        for chunk in iter(lambda: f.read(4096), b''):
            hash_sha256.update(chunk)
            
    return hash_sha256.hexdigest()


def generate_checksum_file(file_path: str, output_dir: Optional[str] = None) -> str:
    """
    Generate a checksum file for the given file.
    
    Args:
        file_path: Path to the file to generate checksum for
        output_dir: Directory to save the checksum file (defaults to same as input file)
        
    Returns:
        Path to the generated checksum file
    """
    # Calculate checksum
    checksum = calculate_checksum(file_path)
    
    # Determine filename and output path
    base_name = os.path.basename(file_path)
    if output_dir is None:
        output_dir = os.path.dirname(file_path)
    
    # Create output filename (remove extension and add .checksum)
    name_without_ext = os.path.splitext(base_name)[0]
    checksum_filename = f"{name_without_ext}.checksum"
    output_path = os.path.join(output_dir, checksum_filename)
    
    # Write checksum to file
    with open(output_path, 'w') as f:
        f.write(checksum)
        
    print(f"Generated checksum file: {output_path}")
    print(f"SHA-256: {checksum}")
    
    return output_path


def process_files(files: List[str], output_dir: Optional[str] = None) -> List[str]:
    """
    Process multiple files and generate checksum files for each.
    
    Args:
        files: List of file paths
        output_dir: Directory to save checksum files
        
    Returns:
        List of paths to generated checksum files
    """
    output_files = []
    
    for file_path in files:
        if not os.path.exists(file_path):
            print(f"Error: File not found: {file_path}")
            continue
            
        try:
            output_file = generate_checksum_file(file_path, output_dir)
            output_files.append(output_file)
        except Exception as e:
            print(f"Error generating checksum for {file_path}: {e}")
            
    return output_files


def main():
    parser = argparse.ArgumentParser(description="Generate checksums for release files")
    parser.add_argument("files", nargs="+", help="Files to generate checksums for")
    parser.add_argument("--output-dir", "-o", help="Directory to save checksum files")
    
    args = parser.parse_args()
    
    process_files(args.files, args.output_dir)
    

if __name__ == "__main__":
    main()