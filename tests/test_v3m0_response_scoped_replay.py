from __future__ import annotations

import copy
from dataclasses import dataclass
import unittest

import rulespace_v3.response as response_module
from rulespace_v3.evidence import canonical_sha
from rulespace_v3.replay_scope import (
    _replay_scope_statistics,
    _scoped_replay_context,
)


@dataclass(frozen=True)
class _Payload:
    value: int


@dataclass(frozen=True)
class _RegistryEntry:
    control_id: str


@dataclass(frozen=True)
class _ReferenceSpec:
    control_registry_entry: _RegistryEntry
    candidate_fejer_order: int


@dataclass(frozen=True)
class _AttemptAudit:
    shell_spec: str


@dataclass(frozen=True)
class _Outcome:
    marker: int
    reference_spec: _ReferenceSpec
    attempt_audit: _AttemptAudit
    reference: _Payload
    shell: _Payload
    paired_response: _Payload


def _outcome(marker: int = 1) -> _Outcome:
    return _Outcome(
        marker=marker,
        reference_spec=_ReferenceSpec(
            control_registry_entry=_RegistryEntry("full"),
            candidate_fejer_order=256,
        ),
        attempt_audit=_AttemptAudit("shell-spec"),
        reference=_Payload(11),
        shell=_Payload(13),
        paired_response=_Payload(17),
    )


def _preflight(value: object) -> None:
    if type(value) is not _Outcome:
        raise TypeError("outcome has the wrong exact type")
    if type(value.marker) is not int:
        raise TypeError("marker has the wrong exact type")
    if (
        type(value.reference_spec) is not _ReferenceSpec
        or type(value.reference_spec.control_registry_entry)
        is not _RegistryEntry
        or type(value.reference_spec.control_registry_entry.control_id) is not str
        or type(value.reference_spec.candidate_fejer_order) is not int
    ):
        raise TypeError("reference_spec has the wrong exact type")
    if (
        type(value.attempt_audit) is not _AttemptAudit
        or type(value.attempt_audit.shell_spec) is not str
    ):
        raise TypeError("attempt_audit has the wrong exact type")
    for field in ("reference", "shell", "paired_response"):
        payload = getattr(value, field)
        if type(payload) is not _Payload or type(payload.value) is not int:
            raise TypeError(f"{field} has the wrong exact type")


def _digest(value: object) -> str:
    _preflight(value)
    return canonical_sha(
        {
            "marker": value.marker,
            "control_id": value.reference_spec.control_registry_entry.control_id,
            "candidate_fejer_order": value.reference_spec.candidate_fejer_order,
            "shell_spec": value.attempt_audit.shell_spec,
            "reference": value.reference.value,
            "shell": value.shell.value,
            "paired_response": value.paired_response.value,
        }
    )


def _seal(schema: str, digest: str) -> str:
    return canonical_sha({"schema": schema, "digest": digest})


def _accept_binding(_authority: object) -> None:
    return None


@dataclass(frozen=True)
class _AuthorityCase:
    namespace: str
    exposed_field: str
    wrapper_slot: str
    build: object
    issue: object
    reverify: object
    outcome_property: object
    build_args: tuple[object, ...]
    authority_binding_field: str
    replay_count: list[int]


def _make_case(kind: str) -> _AuthorityCase:
    replay_count = [0]

    def expected(*_args: object) -> _Outcome:
        replay_count[0] += 1
        return _outcome()

    shared = tuple(object() for _ in range(9))
    if kind == "reference":
        (
            build,
            _verify,
            issue,
            reverify,
            outcome_property,
            _payload_property,
        ) = response_module._make_closed_reference_authority(
            expected,
            _preflight,
            _digest,
            _seal,
            clone=copy.deepcopy,
            binding_validator=_accept_binding,
        )
        return _AuthorityCase(
            namespace=(
                "rulespace_v3.response.VerifiedEndpointReferenceOutcome"
            ),
            exposed_field="reference",
            wrapper_slot="_VerifiedEndpointReferenceOutcome__outcome",
            build=build,
            issue=issue,
            reverify=reverify,
            outcome_property=outcome_property,
            build_args=shared[:7],
            authority_binding_field="registry",
            replay_count=replay_count,
        )
    if kind == "shell":
        (
            _build_spec,
            build,
            _verify,
            issue,
            reverify,
            outcome_property,
            _payload_property,
        ) = response_module._make_closed_shell_authority(
            expected,
            lambda *_args: object(),
            _preflight,
            _digest,
            _seal,
            clone=copy.deepcopy,
            binding_validator=_accept_binding,
        )
        return _AuthorityCase(
            namespace="rulespace_v3.response.VerifiedEndpointShellOutcome",
            exposed_field="shell",
            wrapper_slot="_VerifiedEndpointShellOutcome__outcome",
            build=build,
            issue=issue,
            reverify=reverify,
            outcome_property=outcome_property,
            build_args=shared[:7],
            authority_binding_field="reference",
            replay_count=replay_count,
        )
    if kind == "paired":
        (
            build,
            _verify,
            issue,
            reverify,
            outcome_property,
            _payload_property,
        ) = response_module._make_closed_paired_authority(
            expected,
            lambda *_args: shared,
            _preflight,
            _digest,
            _seal,
            clone=copy.deepcopy,
            binding_validator=_accept_binding,
        )
        return _AuthorityCase(
            namespace="rulespace_v3.response.VerifiedPairedResponseOutcome",
            exposed_field="paired_response",
            wrapper_slot="_VerifiedPairedResponseOutcome__outcome",
            build=build,
            issue=issue,
            reverify=reverify,
            outcome_property=outcome_property,
            build_args=shared,
            authority_binding_field="inputs",
            replay_count=replay_count,
        )
    raise AssertionError(f"unknown authority kind {kind}")


def _live_authority(reverify: object, wrapper: object) -> object:
    for cell in reverify.__closure__ or ():
        candidate = cell.cell_contents
        if type(candidate) is dict and id(wrapper) in candidate:
            return candidate[id(wrapper)][1]
    raise AssertionError("authority live registry was not found")


class ResponseAuthorityScopedReplayTests(unittest.TestCase):
    kinds = ("reference", "shell", "paired")

    def test_issue_records_one_full_replay_and_properties_are_guarded_hits(self):
        for kind in self.kinds:
            with self.subTest(kind=kind):
                case = _make_case(kind)
                with _scoped_replay_context():
                    wrapper = case.build(*case.build_args)
                    first = case.outcome_property(wrapper)
                    second = case.outcome_property(wrapper)
                    statistics = _replay_scope_statistics()

                self.assertEqual(first, _outcome())
                self.assertEqual(second, _outcome())
                self.assertIsNot(first, second)
                self.assertEqual(case.replay_count, [1])
                self.assertEqual(
                    dict(statistics.full_records)[case.namespace],
                    1,
                )
                self.assertEqual(dict(statistics.hits)[case.namespace], 2)

    def test_no_scope_and_each_fresh_scope_require_independent_full_replay(self):
        for kind in self.kinds:
            with self.subTest(kind=kind):
                case = _make_case(kind)
                wrapper = case.build(*case.build_args)
                case.outcome_property(wrapper)
                case.outcome_property(wrapper)
                self.assertEqual(case.replay_count, [3])

                with _scoped_replay_context():
                    case.outcome_property(wrapper)
                    case.outcome_property(wrapper)
                    first_scope = _replay_scope_statistics()
                self.assertEqual(case.replay_count, [4])
                self.assertEqual(
                    dict(first_scope.full_records)[case.namespace],
                    1,
                )
                self.assertEqual(dict(first_scope.hits)[case.namespace], 1)

                with _scoped_replay_context():
                    case.outcome_property(wrapper)
                self.assertEqual(case.replay_count, [5])

    def test_same_inputs_still_issue_independent_capabilities(self):
        case = _make_case("reference")
        with _scoped_replay_context():
            first = case.build(*case.build_args)
            second = case.build(*case.build_args)
            statistics = _replay_scope_statistics()

        self.assertIsNot(first, second)
        self.assertEqual(case.replay_count, [2])
        self.assertEqual(statistics.entry_count, 2)
        self.assertEqual(dict(statistics.full_records)[case.namespace], 2)

    def test_scope_collapses_the_real_nested_replay_shape_from_11_4_2_to_1_1_1(
        self,
    ):
        def run(*, scoped: bool) -> tuple[int, int, int]:
            counts = {"reference": 0, "shell": 0, "paired": 0}

            def expected_reference(*_args: object) -> _Outcome:
                counts["reference"] += 1
                return _outcome()

            (
                build_reference,
                _verify_reference,
                _issue_reference,
                reverify_reference,
                reference_outcome_property,
                _reference_property,
            ) = response_module._make_closed_reference_authority(
                expected_reference,
                _preflight,
                _digest,
                _seal,
                clone=copy.deepcopy,
                binding_validator=_accept_binding,
            )

            def expected_shell(*args: object) -> _Outcome:
                counts["shell"] += 1
                reference = args[2]
                reverify_reference(reference)
                reverify_reference(reference)
                return _outcome()

            (
                _build_shell_spec,
                build_shell,
                _verify_shell,
                _issue_shell,
                reverify_shell,
                shell_outcome_property,
                _shell_property,
            ) = response_module._make_closed_shell_authority(
                expected_shell,
                lambda *_args: object(),
                _preflight,
                _digest,
                _seal,
                clone=copy.deepcopy,
                binding_validator=_accept_binding,
            )

            def expected_paired(*args: object) -> _Outcome:
                counts["paired"] += 1
                reverify_shell(args[8])
                return _outcome()

            (
                build_paired,
                _verify_paired,
                _issue_paired,
                _reverify_paired,
                paired_outcome_property,
                _paired_property,
            ) = response_module._make_closed_paired_authority(
                expected_paired,
                lambda *_args: (),
                _preflight,
                _digest,
                _seal,
                clone=copy.deepcopy,
                binding_validator=_accept_binding,
            )
            shared = tuple(object() for _ in range(9))

            def execute() -> None:
                reference = build_reference(*shared[:7])
                reference_outcome_property(reference)
                reverify_reference(reference)
                shell = build_shell(
                    shared[0],
                    shared[1],
                    reference,
                    shared[3],
                    shared[4],
                    shared[5],
                    shared[6],
                )
                shell_outcome_property(shell)
                paired = build_paired(*shared[:8], shell)
                paired_outcome_property(paired)

            if scoped:
                with _scoped_replay_context():
                    execute()
            else:
                execute()
            return counts["reference"], counts["shell"], counts["paired"]

        self.assertEqual(run(scoped=False), (11, 4, 2))
        self.assertEqual(run(scoped=True), (1, 1, 1))

    def test_caller_raw_is_never_the_recorded_replay_proof(self):
        for kind in self.kinds:
            with self.subTest(kind=kind):
                case = _make_case(kind)
                caller_raw = _outcome()
                with _scoped_replay_context():
                    wrapper = case.issue(*case.build_args, caller_raw)
                    object.__setattr__(caller_raw.reference, "value", 101)
                    observed = case.outcome_property(wrapper)

                self.assertEqual(observed, _outcome())
                self.assertEqual(case.replay_count, [1])

    def test_cached_hit_rejects_exposed_body_root_or_payload_rebinding(self):
        for kind in self.kinds:
            for target in ("root", "payload"):
                with self.subTest(kind=kind, target=target):
                    case = _make_case(kind)
                    with _scoped_replay_context():
                        wrapper = case.build(*case.build_args)
                        stored = object.__getattribute__(
                            wrapper,
                            case.wrapper_slot,
                        )
                        if target == "root":
                            object.__setattr__(
                                wrapper,
                                case.wrapper_slot,
                                copy.deepcopy(stored),
                            )
                        else:
                            payload = getattr(stored, case.exposed_field)
                            object.__setattr__(
                                stored,
                                case.exposed_field,
                                copy.deepcopy(payload),
                            )
                        with self.assertRaises(ValueError):
                            case.reverify(wrapper)

                    self.assertEqual(case.replay_count, [1])

    def test_cached_hit_rejects_deep_mutation_token_and_seal_changes(self):
        mutations = ("deep-body", "token", "seal")
        for kind in self.kinds:
            for mutation in mutations:
                with self.subTest(kind=kind, mutation=mutation):
                    case = _make_case(kind)
                    with _scoped_replay_context():
                        wrapper = case.build(*case.build_args)
                        stored = object.__getattribute__(
                            wrapper,
                            case.wrapper_slot,
                        )
                        if mutation == "deep-body":
                            payload = getattr(stored, case.exposed_field)
                            object.__setattr__(payload, "value", 103)
                        elif mutation == "token":
                            token_slot = case.wrapper_slot.replace(
                                "__outcome",
                                "__token",
                            )
                            object.__setattr__(wrapper, token_slot, object())
                        else:
                            seal_slot = case.wrapper_slot.replace(
                                "__outcome",
                                "__seal",
                            )
                            object.__setattr__(wrapper, seal_slot, "f" * 64)
                        with self.assertRaises(ValueError):
                            case.reverify(wrapper)

                    self.assertEqual(case.replay_count, [1])

    def test_cached_hit_rejects_authority_snapshot_or_binding_rebind(self):
        for kind in self.kinds:
            for target in ("snapshot", "binding"):
                with self.subTest(kind=kind, target=target):
                    case = _make_case(kind)
                    with _scoped_replay_context():
                        wrapper = case.build(*case.build_args)
                        authority = _live_authority(case.reverify, wrapper)
                        if target == "snapshot":
                            object.__setattr__(
                                authority,
                                "outcome",
                                copy.deepcopy(authority.outcome),
                            )
                        elif kind == "paired":
                            object.__setattr__(
                                authority,
                                "inputs",
                                tuple(object() for _ in range(9)),
                            )
                        else:
                            object.__setattr__(
                                authority,
                                case.authority_binding_field,
                                object(),
                            )
                        with self.assertRaises(ValueError):
                            case.reverify(wrapper)

                    self.assertEqual(case.replay_count, [1])


if __name__ == "__main__":
    unittest.main()
