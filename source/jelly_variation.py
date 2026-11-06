"""Generate the optional, checksum-gated, in-memory Mesen appearance patch."""


def cosmetic_patch(rom):
    body = bytearray(rom)

    def offset(cpu):
        return 16 + cpu - 0x8000

    def memory(cpu, size):
        address = offset(cpu)
        return bytes(body[address:address + size])

    def edit(cpu, old, new):
        assert len(old) == len(new) and memory(cpu, len(old)) == old, hex(cpu)
        address = offset(cpu)
        body[address:address + len(new)] = new

    # These AI routines have identical hit, loot and despawn tails. Reuse the
    # first copy. All four incoming branches remain in relative-branch range.
    assert memory(0xA303, 44) == memory(0xA269, 44)
    for pc, dest in ((0xA2BC,0xA27C),(0xA2C7,0xA269),(0xA2D2,0xA290),(0xA2D9,0xA294)):
        old = memory(pc, 2)
        assert pc + 2 + int.from_bytes(old[1:], 'little', signed=True) == dest + 0x9A
        edit(pc, old, bytes([old[0], (dest - pc - 2) & 255]))

    # Equivalent native choice of +$0080 or -$0080 horizontal velocity,
    # followed by the existing jelly animation initializer at $A264.
    old_motion = bytes.fromhex('A5 22 CD 82 06 B0 0B A9 80 85 30 A9 00 85 31 4C FD A2 A9 80 85 30 A9 FF 85 31 A9 38 20 AD 97 60')
    motion = bytes.fromhex('A9 80 85 30 A5 22 CD 82 06 A9 00 90 02 A9 FF 85 31 4C 64 A2')
    assert memory(0xA2E3, len(old_motion)) == old_motion
    edit(0xA2E3, old_motion[:len(motion)], motion)

    # A separate eight-bit XNOR Galois generator advances once per draw. Reset clears
    # $0180 in the unused gap between the PPU upload buffer and hardware stack.
    # Its 255-state orbit omits $D0. Reject low pair 00, leaving exactly 64
    # symbols for each of 01 (amber), 10 (blue), and 11 (moon).
    spawn = bytes.fromhex(
        'AD 80 01 4A B0 02 49 B8 8D 80 01 29 03 F0 F1 '
        '45 3E 29 03 45 3E 85 3E '
        'A9 C0 85 20 60')
    # The renderer has just read the high byte of the current metasprite
    # pointer into A. These three consecutive animation records are the
    # jellyfish's three pulse poses. All other actors take the common exit.
    #
    # Compare the low byte only after testing the bank. Assign a palette once
    # per actor, before the stock four-cell loop. That loop stays byte-identical.
    draw = bytes.fromhex(
        'C9 B8 D0 12 A5 06 E9 7E C9 27 B0 0A '
        'A0 1E B1 40 29 03 05 00 85 00 '
        'A0 00 84 01 60')            # original LDY #0 / STY $01
    start = 0xA2E3 + len(motion)
    draw_start = start + len(spawn)
    assert draw_start + len(draw) <= 0xA32F
    code = spawn + draw
    edit(start, memory(start, len(code)), code)
    # The normal and doubled-height collision helpers have identical tails.
    # Preserve their original CLC and all subsequent operations with one jump.
    assert memory(0x9A17,32) == memory(0x99F4,32)
    edit(0x9A17,bytes.fromhex('18 6D 3C'),bytes.fromhex('4C F4 99'))
    # First spawn seeds from native entropy without advancing it. $00 never
    # survives an accepted draw. Guard $D0, the generator's one fixed point.
    # Rejections loop inside spawn, so passing through zero cannot reseed.
    seeded = bytes.fromhex(
        'AD 80 01 F0 04 C9 D0 D0 11 '
        'AD 24 03 4D 25 03 45 46 C9 D0 D0 02 A9 00 8D 80 01 '
        '4C') + start.to_bytes(2,'little')
    assert 0x9A1A + len(seeded) <= 0x9A37
    edit(0x9A1A, memory(0x9A1A,len(seeded)),seeded)
    for pc in (0xA229,0xA2A5,0xD31B):
        edit(pc, bytes.fromhex('A9 C0 85 20'), bytes.fromhex('20 1A 9A EA'))
    edit(0x9AC8,bytes.fromhex('A0 00 84 01'), b'\x20' + draw_start.to_bytes(2,'little') + b'\xea')

    # Include just the deltas. The user's original ROM is read-only.
    output = bytearray(b'PATCH')
    i = 0
    while i < len(body):
        if body[i] == rom[i]:
            i += 1
            continue
        first = i
        while i < len(body) and body[i] != rom[i]:
            i += 1
        output += first.to_bytes(3,'big') + (i-first).to_bytes(2,'big') + body[first:i]
    return bytes(output + b'EOF')
