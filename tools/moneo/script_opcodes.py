"""Auto-generated FRLG script opcode table from pokefirered event.inc."""
# DO NOT EDIT by hand -- regenerate via tools/moneo/_gen_opcodes.py

# Each entry: opcode_byte -> {mnemonic, length, ptr_offsets, args}
#   length=None means variable-length (handle specially)
#   ptr_offsets are byte offsets within the instruction where 4-byte ROM ptrs live
OPCODES: dict[int, dict] = {
    0x00: {"mnemonic": 'nop', "length": 1, "ptr_offsets": [], "args": ''},
    0x01: {"mnemonic": 'nop1', "length": 1, "ptr_offsets": [], "args": ''},
    0x02: {"mnemonic": 'end', "length": 1, "ptr_offsets": [], "args": ''},
    0x03: {"mnemonic": 'return', "length": 1, "ptr_offsets": [], "args": ''},
    0x04: {"mnemonic": 'call', "length": 5, "ptr_offsets": [1], "args": 'destination:req'},
    0x05: {"mnemonic": 'goto', "length": 5, "ptr_offsets": [1], "args": 'destination:req'},
    0x06: {"mnemonic": 'goto_if', "length": 6, "ptr_offsets": [2], "args": 'condition:req, destination:req'},
    0x07: {"mnemonic": 'call_if', "length": 6, "ptr_offsets": [2], "args": 'condition:req, destination:req'},
    0x08: {"mnemonic": 'gotostd', "length": 2, "ptr_offsets": [], "args": 'function:req'},
    0x09: {"mnemonic": 'callstd', "length": 2, "ptr_offsets": [], "args": 'function:req'},
    0x0A: {"mnemonic": 'gotostd_if', "length": 3, "ptr_offsets": [], "args": 'condition:req, function:req'},
    0x0B: {"mnemonic": 'callstd_if', "length": 3, "ptr_offsets": [], "args": 'condition:req, function:req'},
    0x0C: {"mnemonic": 'returnram', "length": 1, "ptr_offsets": [], "args": ''},
    0x0D: {"mnemonic": 'endram', "length": 1, "ptr_offsets": [], "args": ''},
    0x0E: {"mnemonic": 'setmysteryeventstatus', "length": 2, "ptr_offsets": [], "args": 'value:req'},
    0x0F: {"mnemonic": 'loadword', "length": 6, "ptr_offsets": [2], "args": 'destIndex:req, value:req'},
    0x10: {"mnemonic": 'loadbyte', "length": 3, "ptr_offsets": [], "args": 'destIndex:req, value:req'},
    0x11: {"mnemonic": 'setptr', "length": 6, "ptr_offsets": [2], "args": 'value:req, ptr:req'},
    0x12: {"mnemonic": 'loadbytefromptr', "length": 6, "ptr_offsets": [2], "args": 'destIndex:req, source:req'},
    0x13: {"mnemonic": 'setptrbyte', "length": 6, "ptr_offsets": [2], "args": 'srcIndex:req, destination:req'},
    0x14: {"mnemonic": 'copylocal', "length": 3, "ptr_offsets": [], "args": 'destIndex:req, srcIndex:req'},
    0x15: {"mnemonic": 'copybyte', "length": 9, "ptr_offsets": [1, 5], "args": 'destination:req, source:req'},
    0x16: {"mnemonic": 'setvar', "length": 5, "ptr_offsets": [], "args": 'destination:req, value:req'},
    0x17: {"mnemonic": 'addvar', "length": 5, "ptr_offsets": [], "args": 'destination:req, value:req'},
    0x18: {"mnemonic": 'subvar', "length": 5, "ptr_offsets": [], "args": 'destination:req, value:req'},
    0x19: {"mnemonic": 'copyvar', "length": 5, "ptr_offsets": [], "args": 'destination:req, source:req'},
    0x1A: {"mnemonic": 'setorcopyvar', "length": 5, "ptr_offsets": [], "args": 'destination:req, source:req'},
    0x1B: {"mnemonic": 'compare_local_to_local', "length": 3, "ptr_offsets": [], "args": 'local1:req, local2:req'},
    0x1C: {"mnemonic": 'compare_local_to_value', "length": 3, "ptr_offsets": [], "args": 'local:req, value:req'},
    0x1D: {"mnemonic": 'compare_local_to_ptr', "length": 6, "ptr_offsets": [2], "args": 'local:req, ptr:req'},
    0x1E: {"mnemonic": 'compare_ptr_to_local', "length": 6, "ptr_offsets": [1], "args": 'ptr:req, local:req'},
    0x1F: {"mnemonic": 'compare_ptr_to_value', "length": 6, "ptr_offsets": [1], "args": 'ptr:req, value:req'},
    0x20: {"mnemonic": 'compare_ptr_to_ptr', "length": 9, "ptr_offsets": [1, 5], "args": 'ptr1:req, ptr2:req'},
    0x21: {"mnemonic": 'compare_var_to_value', "length": 5, "ptr_offsets": [], "args": 'var:req, value:req'},
    0x22: {"mnemonic": 'compare_var_to_var', "length": 5, "ptr_offsets": [], "args": 'var1:req, var2:req'},
    0x23: {"mnemonic": 'callnative', "length": 5, "ptr_offsets": [1], "args": 'func:req'},
    0x24: {"mnemonic": 'gotonative', "length": 5, "ptr_offsets": [1], "args": 'func:req'},
    0x25: {"mnemonic": 'special', "length": 3, "ptr_offsets": [], "args": 'function:req'},
    0x26: {"mnemonic": 'specialvar', "length": 5, "ptr_offsets": [], "args": 'output:req, function:req'},
    0x27: {"mnemonic": 'waitstate', "length": 1, "ptr_offsets": [], "args": ''},
    0x28: {"mnemonic": 'delay', "length": 3, "ptr_offsets": [], "args": 'frames:req'},
    0x29: {"mnemonic": 'setflag', "length": 3, "ptr_offsets": [], "args": 'flag:req'},
    0x2A: {"mnemonic": 'clearflag', "length": 3, "ptr_offsets": [], "args": 'flag:req'},
    0x2B: {"mnemonic": 'checkflag', "length": 3, "ptr_offsets": [], "args": 'flag:req'},
    0x2C: {"mnemonic": 'initclock', "length": 5, "ptr_offsets": [], "args": 'hour:req, minute:req'},
    0x2D: {"mnemonic": 'dotimebasedevents', "length": 1, "ptr_offsets": [], "args": ''},
    0x2E: {"mnemonic": 'gettime', "length": 1, "ptr_offsets": [], "args": ''},
    0x2F: {"mnemonic": 'playse', "length": 3, "ptr_offsets": [], "args": 'song:req'},
    0x30: {"mnemonic": 'waitse', "length": 1, "ptr_offsets": [], "args": ''},
    0x31: {"mnemonic": 'playfanfare', "length": 3, "ptr_offsets": [], "args": 'song:req'},
    0x32: {"mnemonic": 'waitfanfare', "length": 1, "ptr_offsets": [], "args": ''},
    0x33: {"mnemonic": 'playbgm', "length": 4, "ptr_offsets": [], "args": 'song:req, save_song:req'},
    0x34: {"mnemonic": 'savebgm', "length": 3, "ptr_offsets": [], "args": 'song:req'},
    0x35: {"mnemonic": 'fadedefaultbgm', "length": 1, "ptr_offsets": [], "args": ''},
    0x36: {"mnemonic": 'fadenewbgm', "length": 3, "ptr_offsets": [], "args": 'song:req'},
    0x37: {"mnemonic": 'fadeoutbgm', "length": 2, "ptr_offsets": [], "args": 'speed:req'},
    0x38: {"mnemonic": 'fadeinbgm', "length": 2, "ptr_offsets": [], "args": 'speed:req'},
    0x39: {"mnemonic": 'warp', "length": None, "ptr_offsets": [], "args": 'map:req, a, b, c'},
    0x3A: {"mnemonic": 'warpsilent', "length": None, "ptr_offsets": [], "args": 'map:req, a, b, c'},
    0x3B: {"mnemonic": 'warpdoor', "length": None, "ptr_offsets": [], "args": 'map:req, a, b, c'},
    0x3C: {"mnemonic": 'warphole', "length": None, "ptr_offsets": [], "args": 'map:req'},
    0x3D: {"mnemonic": 'warpteleport', "length": None, "ptr_offsets": [], "args": 'map:req, a, b, c'},
    0x3E: {"mnemonic": 'setwarp', "length": None, "ptr_offsets": [], "args": 'map:req, a, b, c'},
    0x3F: {"mnemonic": 'setdynamicwarp', "length": None, "ptr_offsets": [], "args": 'map:req, a, b, c'},
    0x40: {"mnemonic": 'setdivewarp', "length": None, "ptr_offsets": [], "args": 'map:req, a, b, c'},
    0x41: {"mnemonic": 'setholewarp', "length": None, "ptr_offsets": [], "args": 'map:req, a=0, b=0, c'},
    0x42: {"mnemonic": 'getplayerxy', "length": 5, "ptr_offsets": [], "args": 'x:req, y:req'},
    0x43: {"mnemonic": 'getpartysize', "length": 1, "ptr_offsets": [], "args": ''},
    0x44: {"mnemonic": 'additem', "length": 5, "ptr_offsets": [], "args": 'itemId:req, quantity=1'},
    0x45: {"mnemonic": 'removeitem', "length": 5, "ptr_offsets": [], "args": 'itemId:req, quantity=1'},
    0x46: {"mnemonic": 'checkitemspace', "length": 5, "ptr_offsets": [], "args": 'itemId:req, quantity=1'},
    0x47: {"mnemonic": 'checkitem', "length": 5, "ptr_offsets": [], "args": 'itemId:req, quantity=1'},
    0x48: {"mnemonic": 'checkitemtype', "length": 3, "ptr_offsets": [], "args": 'itemId:req'},
    0x49: {"mnemonic": 'addpcitem', "length": 5, "ptr_offsets": [], "args": 'itemId:req, quantity=1'},
    0x4A: {"mnemonic": 'checkpcitem', "length": 5, "ptr_offsets": [], "args": 'itemId:req, quantity=1'},
    0x4B: {"mnemonic": 'adddecoration', "length": 3, "ptr_offsets": [], "args": 'decoration:req'},
    0x4C: {"mnemonic": 'removedecoration', "length": 3, "ptr_offsets": [], "args": 'decoration:req'},
    0x4D: {"mnemonic": 'checkdecor', "length": 3, "ptr_offsets": [], "args": 'decoration:req'},
    0x4E: {"mnemonic": 'checkdecorspace', "length": 3, "ptr_offsets": [], "args": 'decoration:req'},
    0x57: {"mnemonic": 'setobjectxy', "length": 7, "ptr_offsets": [], "args": 'localId:req, x:req, y:req'},
    0x58: {"mnemonic": 'showobjectat', "length": None, "ptr_offsets": [], "args": 'localId:req, map:req'},
    0x59: {"mnemonic": 'hideobjectat', "length": None, "ptr_offsets": [], "args": 'localId:req, map:req'},
    0x5A: {"mnemonic": 'faceplayer', "length": 1, "ptr_offsets": [], "args": ''},
    0x5B: {"mnemonic": 'turnobject', "length": 4, "ptr_offsets": [], "args": 'localId:req, direction:req'},
    0x5C: {"mnemonic": 'trainerbattle', "length": None, "ptr_offsets": [], "args": 'type:req, trainer:req, local_id:req, pointer1:req, pointer2, pointer3, pointer4'},
    0x5D: {"mnemonic": 'dotrainerbattle', "length": 1, "ptr_offsets": [], "args": ''},
    0x5E: {"mnemonic": 'gotopostbattlescript', "length": 1, "ptr_offsets": [], "args": ''},
    0x5F: {"mnemonic": 'gotobeatenscript', "length": 1, "ptr_offsets": [], "args": ''},
    0x60: {"mnemonic": 'checktrainerflag', "length": 3, "ptr_offsets": [], "args": 'trainer:req'},
    0x61: {"mnemonic": 'settrainerflag', "length": 3, "ptr_offsets": [], "args": 'trainer:req'},
    0x62: {"mnemonic": 'cleartrainerflag', "length": 3, "ptr_offsets": [], "args": 'trainer:req'},
    0x63: {"mnemonic": 'setobjectxyperm', "length": 7, "ptr_offsets": [], "args": 'localId:req, x:req, y:req'},
    0x64: {"mnemonic": 'copyobjectxytoperm', "length": 3, "ptr_offsets": [], "args": 'localId:req'},
    0x65: {"mnemonic": 'setobjectmovementtype', "length": 4, "ptr_offsets": [], "args": 'localId:req, movementType:req'},
    0x66: {"mnemonic": 'waitmessage', "length": 1, "ptr_offsets": [], "args": ''},
    0x67: {"mnemonic": 'message', "length": 5, "ptr_offsets": [1], "args": 'text:req'},
    0x68: {"mnemonic": 'closemessage', "length": 1, "ptr_offsets": [], "args": ''},
    0x69: {"mnemonic": 'lockall', "length": 1, "ptr_offsets": [], "args": ''},
    0x6A: {"mnemonic": 'lock', "length": 1, "ptr_offsets": [], "args": ''},
    0x6B: {"mnemonic": 'releaseall', "length": 1, "ptr_offsets": [], "args": ''},
    0x6C: {"mnemonic": 'release', "length": 1, "ptr_offsets": [], "args": ''},
    0x6D: {"mnemonic": 'waitbuttonpress', "length": 1, "ptr_offsets": [], "args": ''},
    0x6E: {"mnemonic": 'yesnobox', "length": 3, "ptr_offsets": [], "args": 'x:req, y:req'},
    0x6F: {"mnemonic": 'multichoice', "length": 5, "ptr_offsets": [], "args": 'x:req, y:req, multichoiceId:req, ignoreBPress:req'},
    0x70: {"mnemonic": 'multichoicedefault', "length": 6, "ptr_offsets": [], "args": 'x:req, y:req, multichoiceId:req, default:req, ignoreBPress:req'},
    0x71: {"mnemonic": 'multichoicegrid', "length": 6, "ptr_offsets": [], "args": 'x:req, y:req, multichoiceId:req, per_row:req, ignoreBPress:req'},
    0x72: {"mnemonic": 'drawbox', "length": 1, "ptr_offsets": [], "args": ''},
    0x73: {"mnemonic": 'erasebox', "length": 5, "ptr_offsets": [], "args": 'left:req, top:req, right:req, bottom:req'},
    0x74: {"mnemonic": 'drawboxtext', "length": 5, "ptr_offsets": [], "args": 'left:req, top:req, multichoiceId:req, ignoreBPress:req'},
    0x75: {"mnemonic": 'showmonpic', "length": 5, "ptr_offsets": [], "args": 'species:req, x:req, y:req'},
    0x76: {"mnemonic": 'hidemonpic', "length": 1, "ptr_offsets": [], "args": ''},
    0x77: {"mnemonic": 'showcontestpainting', "length": 2, "ptr_offsets": [], "args": 'winnerId:req'},
    0x78: {"mnemonic": 'braillemessage', "length": 5, "ptr_offsets": [1], "args": 'text:req'},
    0x79: {"mnemonic": 'givemon', "length": 15, "ptr_offsets": [6, 10], "args": 'species:req, level:req, item=ITEM_NONE'},
    0x7A: {"mnemonic": 'giveegg', "length": 3, "ptr_offsets": [], "args": 'species:req'},
    0x7B: {"mnemonic": 'setmonmove', "length": 5, "ptr_offsets": [], "args": 'partyIndex:req, slot:req, move:req'},
    0x7C: {"mnemonic": 'checkpartymove', "length": 3, "ptr_offsets": [], "args": 'move:req'},
    0x7D: {"mnemonic": 'bufferspeciesname', "length": None, "ptr_offsets": [], "args": 'stringVarId:req, species:req'},
    0x7E: {"mnemonic": 'bufferleadmonspeciesname', "length": None, "ptr_offsets": [], "args": 'stringVarId:req'},
    0x7F: {"mnemonic": 'bufferpartymonnick', "length": None, "ptr_offsets": [], "args": 'stringVarId:req, slot:req'},
    0x80: {"mnemonic": 'bufferitemname', "length": None, "ptr_offsets": [], "args": 'stringVarId:req, item:req'},
    0x81: {"mnemonic": 'bufferdecorationname', "length": None, "ptr_offsets": [], "args": 'stringVarId:req, decoration:req'},
    0x82: {"mnemonic": 'buffermovename', "length": None, "ptr_offsets": [], "args": 'stringVarId:req, move:req'},
    0x83: {"mnemonic": 'buffernumberstring', "length": None, "ptr_offsets": [], "args": 'stringVarId:req, input:req'},
    0x84: {"mnemonic": 'bufferstdstring', "length": None, "ptr_offsets": [], "args": 'stringVarId:req, index:req'},
    0x85: {"mnemonic": 'bufferstring', "length": None, "ptr_offsets": [], "args": 'stringVarId:req, text:req'},
    0x86: {"mnemonic": 'pokemart', "length": 5, "ptr_offsets": [1], "args": 'products:req'},
    0x87: {"mnemonic": 'pokemartdecoration', "length": 5, "ptr_offsets": [1], "args": 'products:req'},
    0x88: {"mnemonic": 'pokemartdecoration2', "length": 5, "ptr_offsets": [1], "args": 'products:req'},
    0x89: {"mnemonic": 'playslotmachine', "length": 3, "ptr_offsets": [], "args": 'id:req'},
    0x8A: {"mnemonic": 'setberrytree', "length": 4, "ptr_offsets": [], "args": 'treeId:req, berry:req, growthStage:req'},
    0x8B: {"mnemonic": 'choosecontestmon', "length": 1, "ptr_offsets": [], "args": ''},
    0x8C: {"mnemonic": 'startcontest', "length": 1, "ptr_offsets": [], "args": ''},
    0x8D: {"mnemonic": 'showcontestresults', "length": 1, "ptr_offsets": [], "args": ''},
    0x8E: {"mnemonic": 'contestlinktransfer', "length": 1, "ptr_offsets": [], "args": ''},
    0x8F: {"mnemonic": 'random', "length": 3, "ptr_offsets": [], "args": 'limit:req'},
    0x90: {"mnemonic": 'addmoney', "length": 6, "ptr_offsets": [1], "args": 'value:req, disable=0'},
    0x91: {"mnemonic": 'removemoney', "length": 6, "ptr_offsets": [1], "args": 'value:req, disable=0'},
    0x92: {"mnemonic": 'checkmoney', "length": 6, "ptr_offsets": [1], "args": 'value:req, disable=0'},
    0x93: {"mnemonic": 'showmoneybox', "length": 4, "ptr_offsets": [], "args": 'x:req, y:req, disable=0'},
    0x94: {"mnemonic": 'hidemoneybox', "length": 3, "ptr_offsets": [], "args": ''},
    0x95: {"mnemonic": 'updatemoneybox', "length": 4, "ptr_offsets": [], "args": 'disable=0'},
    0x96: {"mnemonic": 'getpokenewsactive', "length": 3, "ptr_offsets": [], "args": 'newsKind:req'},
    0x97: {"mnemonic": 'fadescreen', "length": 2, "ptr_offsets": [], "args": 'mode:req'},
    0x98: {"mnemonic": 'fadescreenspeed', "length": 3, "ptr_offsets": [], "args": 'mode:req, speed:req'},
    0x99: {"mnemonic": 'setflashlevel', "length": 3, "ptr_offsets": [], "args": 'level:req'},
    0x9A: {"mnemonic": 'animateflash', "length": 2, "ptr_offsets": [], "args": 'level:req'},
    0x9B: {"mnemonic": 'messageautoscroll', "length": 5, "ptr_offsets": [1], "args": 'text:req'},
    0x9C: {"mnemonic": 'dofieldeffect', "length": 3, "ptr_offsets": [], "args": 'animation:req'},
    0x9D: {"mnemonic": 'setfieldeffectargument', "length": 4, "ptr_offsets": [], "args": 'argNum:req, value:req'},
    0x9E: {"mnemonic": 'waitfieldeffect', "length": 3, "ptr_offsets": [], "args": 'animation:req'},
    0x9F: {"mnemonic": 'setrespawn', "length": 3, "ptr_offsets": [], "args": 'heallocation:req'},
    0xA0: {"mnemonic": 'checkplayergender', "length": 1, "ptr_offsets": [], "args": ''},
    0xA1: {"mnemonic": 'playmoncry', "length": 5, "ptr_offsets": [], "args": 'species:req, mode:req'},
    0xA2: {"mnemonic": 'setmetatile', "length": 9, "ptr_offsets": [], "args": 'x:req, y:req, metatileId:req, impassable:req'},
    0xA3: {"mnemonic": 'resetweather', "length": 1, "ptr_offsets": [], "args": ''},
    0xA4: {"mnemonic": 'setweather', "length": 3, "ptr_offsets": [], "args": 'type:req'},
    0xA5: {"mnemonic": 'doweather', "length": 1, "ptr_offsets": [], "args": ''},
    0xA6: {"mnemonic": 'setstepcallback', "length": 2, "ptr_offsets": [], "args": 'stepCbId:req'},
    0xA7: {"mnemonic": 'setmaplayoutindex', "length": 3, "ptr_offsets": [], "args": 'index:req'},
    0xA8: {"mnemonic": 'setobjectsubpriority', "length": None, "ptr_offsets": [], "args": 'localId:req, map:req, subpriority:req'},
    0xA9: {"mnemonic": 'resetobjectsubpriority', "length": None, "ptr_offsets": [], "args": 'localId:req, map:req'},
    0xAA: {"mnemonic": 'createvobject', "length": 9, "ptr_offsets": [], "args": 'graphicsId:req, id:req, x:req, y:req, elevation=3, direction=DIR_SOUTH'},
    0xAB: {"mnemonic": 'turnvobject', "length": 3, "ptr_offsets": [], "args": 'id:req, direction:req'},
    0xAC: {"mnemonic": 'opendoor', "length": 5, "ptr_offsets": [], "args": 'x:req, y:req'},
    0xAD: {"mnemonic": 'closedoor', "length": 5, "ptr_offsets": [], "args": 'x:req, y:req'},
    0xAE: {"mnemonic": 'waitdooranim', "length": 1, "ptr_offsets": [], "args": ''},
    0xAF: {"mnemonic": 'setdooropen', "length": 5, "ptr_offsets": [], "args": 'x:req, y:req'},
    0xB0: {"mnemonic": 'setdoorclosed', "length": 5, "ptr_offsets": [], "args": 'x:req, y:req'},
    0xB1: {"mnemonic": 'addelevmenuitem', "length": 8, "ptr_offsets": [], "args": 'a:req, b:req, c:req, d:req'},
    0xB2: {"mnemonic": 'showelevmenu', "length": 1, "ptr_offsets": [], "args": ''},
    0xB3: {"mnemonic": 'checkcoins', "length": 3, "ptr_offsets": [], "args": 'out:req'},
    0xB4: {"mnemonic": 'addcoins', "length": 3, "ptr_offsets": [], "args": 'count:req'},
    0xB5: {"mnemonic": 'removecoins', "length": 3, "ptr_offsets": [], "args": 'count:req'},
    0xB6: {"mnemonic": 'setwildbattle', "length": 6, "ptr_offsets": [], "args": 'species:req, level:req, item=ITEM_NONE'},
    0xB7: {"mnemonic": 'dowildbattle', "length": 1, "ptr_offsets": [], "args": ''},
    0xB8: {"mnemonic": 'setvaddress', "length": 5, "ptr_offsets": [1], "args": 'pointer:req'},
    0xB9: {"mnemonic": 'vgoto', "length": 5, "ptr_offsets": [1], "args": 'destination:req'},
    0xBA: {"mnemonic": 'vcall', "length": 5, "ptr_offsets": [1], "args": 'destination:req'},
    0xBB: {"mnemonic": 'vgoto_if', "length": 6, "ptr_offsets": [2], "args": 'condition:req, destination:req'},
    0xBC: {"mnemonic": 'vcall_if', "length": 6, "ptr_offsets": [2], "args": 'condition:req, destination:req'},
    0xBD: {"mnemonic": 'vmessage', "length": 5, "ptr_offsets": [1], "args": 'text:req'},
    0xBE: {"mnemonic": 'vbuffermessage', "length": 5, "ptr_offsets": [1], "args": 'text:req'},
    0xBF: {"mnemonic": 'vbufferstring', "length": None, "ptr_offsets": [], "args": 'stringVarIndex:req, text:req'},
    0xC0: {"mnemonic": 'showcoinsbox', "length": 3, "ptr_offsets": [], "args": 'x:req, y:req'},
    0xC1: {"mnemonic": 'hidecoinsbox', "length": 3, "ptr_offsets": [], "args": 'x:req, y:req'},
    0xC2: {"mnemonic": 'updatecoinsbox', "length": 3, "ptr_offsets": [], "args": 'x:req, y:req'},
    0xC3: {"mnemonic": 'incrementgamestat', "length": 2, "ptr_offsets": [], "args": 'stat:req'},
    0xC4: {"mnemonic": 'setescapewarp', "length": None, "ptr_offsets": [], "args": 'map:req, a, b, c'},
    0xC5: {"mnemonic": 'waitmoncry', "length": 1, "ptr_offsets": [], "args": ''},
    0xC6: {"mnemonic": 'bufferboxname', "length": None, "ptr_offsets": [], "args": 'stringVarId:req, box:req'},
    0xC7: {"mnemonic": 'textcolor', "length": 2, "ptr_offsets": [], "args": 'color:req'},
    0xC8: {"mnemonic": 'loadhelp', "length": 5, "ptr_offsets": [1], "args": 'msg:req'},
    0xC9: {"mnemonic": 'unloadhelp', "length": 1, "ptr_offsets": [], "args": ''},
    0xCA: {"mnemonic": 'signmsg', "length": 1, "ptr_offsets": [], "args": ''},
    0xCB: {"mnemonic": 'normalmsg', "length": 1, "ptr_offsets": [], "args": ''},
    0xCC: {"mnemonic": 'comparestat', "length": 6, "ptr_offsets": [2], "args": 'statId:req, value:req'},
    0xCD: {"mnemonic": 'setmonmodernfatefulencounter', "length": 3, "ptr_offsets": [], "args": 'slot:req'},
    0xCE: {"mnemonic": 'checkmonmodernfatefulencounter', "length": 3, "ptr_offsets": [], "args": 'slot:req'},
    0xCF: {"mnemonic": 'trywondercardscript', "length": 1, "ptr_offsets": [], "args": ''},
    0xD0: {"mnemonic": 'setworldmapflag', "length": 3, "ptr_offsets": [], "args": 'worldmapflag:req'},
    0xD1: {"mnemonic": 'warpspinenter', "length": None, "ptr_offsets": [], "args": 'map:req, a, b, c'},
    0xD2: {"mnemonic": 'setmonmetlocation', "length": 4, "ptr_offsets": [], "args": 'slot:req, location:req'},
    0xD3: {"mnemonic": 'getbraillestringwidth', "length": 5, "ptr_offsets": [1], "args": 'msg:req'},
    0xD4: {"mnemonic": 'bufferitemnameplural', "length": None, "ptr_offsets": [], "args": 'stringVarId:req, item:req, quantity:req'},
}

# Opcodes that load text records (their ptr arg is a TEXT pointer):
TEXT_LOADING_OPCODES = {
    0x67: "message",         # text:4
    0x78: "braillemessage",  # text:4
    0x9B: "messageautoscroll",
    0xBD: "vmessage",
    0xBE: "vbuffermessage",
    0xC8: "loadhelp",
}

# msgbox/msgbox_default/etc. are pseudo-macros expanding to:
#   loadword 0, <text>     (0x0F 0x00 ptr:4) = 6 bytes
#   callstd <type>         (0x09 type:1)     = 2 bytes
# So when 0x0F has destIdx==0 followed by 0x09, the ptr is text.
LOADWORD_OPCODE = 0x0F
CALLSTD_OPCODE = 0x09

# Control flow opcodes (recurse into pointer targets):
CALL_GOTO_OPCODES = {0x04, 0x05}
CALL_GOTO_IF_OPCODES = {0x06, 0x07}

# Terminators (stop walking the script):
END_OPCODES = {0x02, 0x03, 0x0C, 0x0D}  # end, return, returnram, endram

# bufferstring (0x85) and vbufferstring (0xBF) have unusual layouts:
#   .byte 0x85 / 0xBF
#   stringvar <stringVarId>    -- the stringvar macro emits .byte stringVarId
#   .4byte text
# So total = 1 + 1 + 4 = 6 bytes, text ptr at offset +2.
BUFFERSTRING_OPCODES = {0x85, 0xBF}  # ptr at +2, length 6

# trainerbattle (0x5C): subtype byte at +1; layouts depend on subtype.
# We hand-author these from the trainerbattle_* macros in event.inc:
TRAINERBATTLE_LAYOUTS = {
    # subtype: (total_length, [text_ptr_offsets])
    # Header (all subtypes): op:1, type:1, trainer:2, local_id:2 = 6 bytes
    0:  (14, [6, 10]),       # SINGLE:                         intro, lose
    1:  (18, [6, 10]),       # CONTINUE_SCRIPT_NO_MUSIC:       intro, lose, +script@14
    2:  (18, [6, 10]),       # CONTINUE_SCRIPT:                intro, lose, +script@14
    3:  (10, [6]),           # SINGLE_NO_INTRO_TEXT:           lose
    4:  (18, [6, 10, 14]),   # DOUBLE:                         intro, lose, not-enough
    5:  (14, [6, 10]),       # REMATCH:                        intro, lose
    6:  (22, [6, 10, 14]),   # CONTINUE_SCRIPT_DOUBLE:         intro, lose, not-enough, +script@18
    7:  (18, [6, 10, 14]),   # REMATCH_DOUBLE:                 intro, lose, not-enough
    8:  (22, [6, 10, 14]),   # CONTINUE_SCRIPT_DOUBLE_NO_MUSIC: intro, lose, not-enough, +script@18
    9:  (14, [6, 10]),       # EARLY_RIVAL:                    defeat, victory
}
