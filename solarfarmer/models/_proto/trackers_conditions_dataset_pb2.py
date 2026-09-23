# Auto-generated from trackers_conditions_dataset.proto — do not edit by hand.
# Regenerate with:
#   python -m grpc_tools.protoc -I solarfarmer/models/_proto \
#       --python_out=solarfarmer/models/_proto \
#       trackers_conditions_dataset.proto
#
# The serialized FileDescriptorProto bytes below are equivalent to running
# protoc on the accompanying .proto source file.

from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder

_sym_db = _symbol_database.Default()

DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(
    b"\n;solarfarmer/models/_proto/trackers_conditions_dataset.proto"
    b'"#\n\x11ShortArrayWrapper\x12\x0e\n\x06values\x18\x01 \x03(\x05'
    b'"4\n\x14NullableShortWrapper\x12\x12\n\x05value\x18\x01 \x01(\x05'
    b"H\x00\x88\x01\x01B\x08\n\x06_value"
    b'")\n\tLongTuple\x12\r\n\x05item1\x18\x01 \x01(\x03\x12\r\n\x05item2\x18\x02 \x01(\x03'
    b'"\x8d\x03\n\x1cTrackersConditionsDatasetDto'
    b"\x12\x17\n\x0foffset_from_utc\x18\x01 \x01(\x01"
    b"\x12)\n!rotations_are_at_middle_of_period\x18\x02 \x01(\x08"
    b"\x12\x1c\n\x14tracker_rotation_ids\x18\x03 \x03(\t"
    b"\x12.\n!period_in_minutes_for_all_records\x18\x04 \x01(\x01H\x00\x88\x01\x01"
    b'\x12"\n\x0fstart_of_period\x18\x05 \x03(\x0b2\tLongTuple'
    b"\x12\x19\n\x11period_in_minutes\x18\x06 \x03(\x02"
    b"\x129\n\x1etracker_rotations_array_values\x18\x07 \x03(\x0b2\x11ShortArrayWrapper"
    b"\x12;\n\x1dtracker_rotation_unique_value\x18\x08 \x03(\x0b2\x14NullableShortWrapper"
    b'B$\n"_period_in_minutes_for_all_records'
    b"b\x06proto3"
)

_builder.BuildTopDescriptorsAndMessages(
    DESCRIPTOR,
    "solarfarmer/models/_proto/trackers_conditions_dataset.proto",
    globals(),
)
