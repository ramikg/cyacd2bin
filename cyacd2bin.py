import argparse
import binascii
from pathlib import Path

from construct import Byte, Bytes, Checksum, Enum, Int16ub, Int32ub, RawCopy, Struct, this

DEFAULT_FLASH_BYTE_VALUE = b'\x00'

CHECKSUM_TYPE_FLAGS_ENUM = Enum(
    Byte, **{
        "2's complement summation": 0,
        "CRC-16-CCITT": 1,
    }
)

CYACD_HEADER_STRUCT = Struct(
    'silicon_id' / Int32ub,
    'silicon_revision' / Byte,
    'checksum_type' / CHECKSUM_TYPE_FLAGS_ENUM,
)

FLASH_ROW_STRUCT = Struct(
    'fields' / RawCopy(Struct(
        'array_id' / Byte,
        'row_id' / Int16ub,
        'data_length' / Int16ub,
        'data' / Bytes(this.data_length),
    )),
    'checksum' / Checksum(Byte, lambda data: (0x100 - (sum(data) & 0xFF)) % 0x100, this.fields.data)
)


class Cyacd2BinInputAndOutputFilesMustBeDifferent(Exception):
    pass


def _parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument('input', type=argparse.FileType('rb'),
                        help='Input cyacd file.')
    parser.add_argument('--output', '-o',
                        help='Output binary file.')
    parser.add_argument('--default-bit-value', choices=['0', '1'], default='0',
                        help="Used to fill flash rows not present in the cyacd file.")

    return parser.parse_args()


def _print_header(ascii_header):
    header = CYACD_HEADER_STRUCT.parse(binascii.unhexlify(ascii_header))
    print(f'Silicon ID: 0x{header.silicon_id:04X}')
    print(f'Silicon revision: {header.silicon_revision}')
    print(f'Protocol checksum type: {header.checksum_type}')
    print()


def _parse_flash_row(ascii_line):
    return FLASH_ROW_STRUCT.parse(binascii.unhexlify(ascii_line))


def _add_row_to_array(flash_memory, array_id, row_id, row_data):
    if array_id not in flash_memory:
        flash_memory[array_id] = {}

    flash_memory[array_id][row_id] = row_data

    return


def _interval_to_string(start, end):
    assert start <= end
    if start == end:
        return f'{start}'
    else:
        return f'{start}-{end}'


def _get_compact_rows_string(row_ids):
    assert row_ids and len(row_ids) == len(set(row_ids))
    row_ids = sorted(row_ids)
    interval_strings = []
    last_interval_start = row_ids[0]

    for i in range(1, len(row_ids)):
        if row_ids[i] > row_ids[i - 1] + 1:
            interval_strings.append(_interval_to_string(last_interval_start, row_ids[i - 1]))
            last_interval_start = row_ids[i]

    interval_strings.append(_interval_to_string(last_interval_start, row_ids[-1]))

    return ', '.join(interval_strings)


def _write_flash_array_to_file(flash_array, output_file, default_bit_value):
    max_row_number = max(flash_array.keys())
    number_of_rows = max_row_number + 1
    row_length = len(next(iter(flash_array.values())))
    print(f'Present rows {_get_compact_rows_string(flash_array.keys())}')

    for row_id in range(number_of_rows):
        if row_id in flash_array:
            output_file.write(bytes(flash_array[row_id]))
        else:
            byte_value = b'\x00' if default_bit_value == '0' else b'\xFF'
            output_file.write(byte_value * row_length)


def _print_flash_memory_summary(flash_memory):
    plural_string = 's, each' if len(flash_memory.keys()) > 1 else ','
    first_flash_array = next(iter(flash_memory.values()))
    print(f'Found {len(flash_memory.keys())} flash array{plural_string} '
          # Assuming all arrays contain the same number of rows, and that the last row must be flashed
          f'containing {sorted(list(first_flash_array.keys()))[-1] + 1} rows '
          # Assuming all rows contain the same number of bytes
          f'with {len(next(iter(first_flash_array.values())))} bytes each.')


def _write_flash_memory_to_files(flash_memory, output_path, default_bit_value):
    _print_flash_memory_summary(flash_memory)

    with open(output_path, 'wb') as output_file:
        for array_id in flash_memory:
            print(f'Array {array_id}:', end=" ")
            _write_flash_array_to_file(flash_memory[array_id], output_file, default_bit_value)
    print(f'Flash memory written to {Path(output_path).absolute()}')


def parse_cyacd(input_file, output_path, default_bit_value):
    flash_memory = {}

    _print_header(input_file.readline().strip())
    for line in input_file:
        flash_row = _parse_flash_row(line.lstrip(b':').strip()).fields.value

        _add_row_to_array(flash_memory, flash_row.array_id, flash_row.row_id, flash_row.data)

    _write_flash_memory_to_files(flash_memory, output_path, default_bit_value)


if __name__ == '__main__':
    args = _parse_args()

    if args.output and Path(args.output).exists() and Path(args.input.name).samefile(args.output):
        raise Cyacd2BinInputAndOutputFilesMustBeDifferent()

    parse_cyacd(args.input, args.output if args.output else f'{args.input.name}.bin', args.default_bit_value)
