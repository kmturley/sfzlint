# -*- coding: utf-8 -*-
import re
from numbers import Real
from .errors import ValidationError, ValidationWarning
from . import spec
from . import parser


class OpcodeIntRepl:
    '''Converts opcodes with numeric components to their index form, and validates

    for example: OpcodeIntRepl.sub('eq3_bwcc25') -> 'eqN_bwccX'
    validates control codes in cc range.
    for example: OpcodeIntRepl.sub('eq3_bwcc256') -> ValidationError
    '''

    varnames = ['N', 'X', 'Y']
    re = r'([a-z]*)(\d+)'
    # Some opcodes have numbers in the name, we ignore
    ignore = {'vel2', 'cutoff2', 'resonance2', 'wave2'}

    @classmethod
    def sub(cls, token):
        instance = cls(token)
        opcode = re.sub(cls.re, instance, token.value)
        opcode = instance._handle_special_cases(opcode, token)
        return opcode, instance.subs

    def _handle_special_cases(self, opcode, token):
        # order matters here
        if opcode.startswith('varN'):
            return self._handle_varNN(opcode, token)
        elif opcode.startswith('hint_'):
            return self._handle_hint(opcode, token)
        elif opcode.endswith('_mod'):
            return self._handle_mod(opcode, token)
        return opcode

    def _handle_varNN(self, opcode, token):
        # there are four opcodes that break the pattern
        if opcode[:8] in ('varN_mod', 'varN_onc', 'varN_cur'):
            return parser.update_token(token, 'varNN' + opcode[4:])
        self.subs['target'] = parser.update_token(
            token, opcode[5:].replace('X', 'N'))
        return parser.update_token(token, 'varNN_target')

    def _handle_hint(self, opcode, token):
        self.subs['target'] = parser.update_token(
            token, opcode[5:])
        return parser.update_token(token, 'hint_*')

    def _handle_mod(self, opcode, token):
        self.subs['target'] = parser.update_token(
            token, opcode[:-4])
        return parser.update_token(token, '*_mod')

    def __init__(self, raw_opcode):
        self.index = 0
        self.raw = raw_opcode
        self.subs = dict()

    def __call__(self, match):
        if match.group() in self.ignore:
            return match.group()
        try:
            sub = self.varnames[self.index]
            self.index += 1
        except IndexError:
            raise ValidationError(
                f'{self.raw} is not a valid opcode: '
                'unexpected number at {match.group()}',
                self.raw)
        pre, num = match.groups()
        self.subs[sub] = int(num)
        if pre.endswith('cc'):
            _validate_cc_value(int(num), self.raw)
        return pre + sub


def _validate_cc_value(cc_value, token):
    # 0-127 are standard, 128-137 in sfz v2, 140-142 in aria
    if cc_value > 137 and cc_value not in {140, 141, 142}:
        raise ValidationWarning(
            f'{cc_value} is not a valid control code', token)


# most players treat cc, _cc, and _oncc interchangeably
def _try_cc_subs(opcode):
    cc_alts = ('_oncc', '_cc', 'cc')
    for variation in cc_alts:  # order matters
        if variation in opcode:
            for alt in cc_alts:
                if alt != variation:
                    alternative = opcode.replace(variation, alt)
                    if alternative in spec.cc_opcodes:
                        return alternative
    return None


def validate_opcode_expr(raw_opcode, token, config):
    if raw_opcode not in spec.opcodes:
        opcode, subs = OpcodeIntRepl.sub(raw_opcode)
    else:
        opcode = raw_opcode.value
        subs = {}

    if opcode not in spec.opcodes:
        if 'cc' in opcode and 'curvecc' not in opcode:
            new_opcode = _try_cc_subs(opcode)
            if new_opcode:
                validate_opcode_expr(
                    parser.update_token(raw_opcode, new_opcode),
                    token, config)
                raise ValidationWarning(
                    f'undocumented alias of {new_opcode} ({opcode})',
                    raw_opcode)
    try:
        validation = spec.opcodes[opcode]
    except KeyError:
        raise ValidationWarning(
            f'unknown opcode ({opcode})',
            raw_opcode)

    v_type = validation.get('type')
    if v_type and not isinstance(token.value, v_type):
        raise ValidationError(
            f'expected {typenames[v_type]} got {token.value} ({opcode})',
            token)
    spec_versions = config.get('spec_versions')
    if spec_versions and validation['ver'] not in spec_versions:
        raise ValidationError(
            f'opcode spec {validation["ver"]} is not one of {spec_versions}',
            raw_opcode)
    if validation['ver'] == 'cakewalk_v2' and (
            not spec_versions or validation['ver'] not in spec_versions):
        raise ValidationWarning(
            'cakewalk v2 opcodes are not implemented by any player',
            raw_opcode)

    err_msg = validation['validator'].validate(token, config, subs)
    if err_msg:
        msg = f'{err_msg} ({opcode})'
        raise ValidationWarning(msg, token)


typenames = {
    int: 'integer',
    Real: 'integer or float',
    str: 'string',
}
