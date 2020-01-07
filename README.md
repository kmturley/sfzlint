Linter and parser for .sfz files

Unfinished, probably don't use yet

Includes the `sfzlint` command line program:

    sfzlint path/to/file.sfz

To build the linter I built a parser using [Lark](https://github.com/lark-parser/lark).

This may be useful to some people. I've also included the `sfz.ebnf` file. It probably has bugs.
The SFZ file format definition is vague. I had to make some assumptions. For example I assumed unquoted paths
cannot include newlines or `=`.

    from sfzlint.parser import parser
    lark_tree = parser().parse(sfz_string)

Opcode data is from [sfzformat.com](https://sfzformat.com/). I have observed some opcodes in my instruments that are not listed on sfzformat.
For example `pitch_ccN` `volume_onccN` and `fileg_depthccN`. Pondering weather ARIA treats `cc` and `oncc` as interchangeable,
though perhaps these are simply ignored by the player.
