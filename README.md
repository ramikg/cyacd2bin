# cyacd2bin

A Python script for parsing the cyacd (Cypress Application Code and Data) file format, and converting it into binary.

Based on [cyflash](https://github.com/arachnidlabs/cyflash).

## Requirements

- Python 3.6+
- `pip install -Ur requirements.txt`

## Usage example
```bash
python cyacd2bin.py example.cyacd
```

### Example output

```
Silicon ID: 0x1A0911AA
Silicon revision: 0
Protocol checksum type: 2's complement summation

Found 2 flash arrays, each containing 512 rows with 256 bytes each.
Array 0: Present rows 402-511
Array 1: Present rows 0-302, 511
Flash memory written to /tmp/example.cyacd.bin
```