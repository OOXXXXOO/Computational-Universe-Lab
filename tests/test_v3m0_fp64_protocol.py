from __future__ import annotations

import dataclasses
import unittest

from rulespace_v3.evidence import canonical_sha
from rulespace_v3.fp64_protocol import (
    build_fp64_enclosure_protocol,
    fp64_enclosure_protocol_payload,
    verify_fp64_enclosure_protocol,
)
from rulespace_v3.root64 import AUDITED_ROOT64_TABLE_SHA


class Fp64EnclosureProtocolTests(unittest.TestCase):
    def test_protocol_recursively_binds_audited_root64_table(self):
        protocol = build_fp64_enclosure_protocol()
        self.assertEqual(protocol.unit_roundoff_numerator, 1)
        self.assertEqual(
            protocol.unit_roundoff_denominator,
            2**53,
        )
        self.assertEqual(protocol.minimum_subnormal_power_of_two, -1074)
        self.assertEqual(protocol.fma_policy, "forbidden")
        self.assertEqual(protocol.reassociation_policy, "forbidden")
        self.assertEqual(
            protocol.root_interval_table.table_sha,
            AUDITED_ROOT64_TABLE_SHA,
        )
        self.assertEqual(
            verify_fp64_enclosure_protocol(protocol),
            protocol,
        )

    def test_caller_resigned_protocol_cannot_change_policy(self):
        protocol = build_fp64_enclosure_protocol()
        changed = dataclasses.replace(
            protocol,
            protocol_schema_version="caller-policy-v1",
            protocol_sha="0" * 64,
        )
        changed = dataclasses.replace(
            changed,
            protocol_sha=canonical_sha(
                fp64_enclosure_protocol_payload(changed)
            ),
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_fp64_enclosure_protocol(changed)


if __name__ == "__main__":
    unittest.main()
