#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 references/blocks-aliases.json —— 积木友好名 -> 原始 opcode 的对照表。

友好名分两类：
  1. 手写别名：语义直观、跨积木类别唯一（如 move_steps / set_variable / when_receive）
  2. 自动别名：按「类别前缀 + 下划线化」自动生成（如 motion_movesteps -> motion_movesteps）

同时给出每个积木的输入别名（IR 里可用更短的键名写输入）。
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SPEC = os.path.join(ROOT, 'references', 'blocks-spec.json')
OUT = os.path.join(ROOT, 'references', 'blocks-aliases.json')

# ---- 手写别名：语义直观的名字（保留历史别名，向后兼容）----
MANUAL = {
    # 事件
    'when_green_flag_clicked': 'event_whenflagclicked',
    'whenflagclicked': 'event_whenflagclicked',
    'when_receive': 'event_whenbroadcastreceived',
    'whenbroadcastreceived': 'event_whenbroadcastreceived',
    'when_key_pressed': 'event_whenkeypressed',
    'whenkeypressed': 'event_whenkeypressed',
    'when_stage_clicked': 'event_whenstageclicked',
    'when_this_sprite_clicked': 'event_whenthisspriteclicked',
    'when_this_clicked': 'event_whenthisspriteclicked',
    'when_backdrop_switches_to': 'event_whenbackdropswitchesto',
    'when_greater_than': 'event_whengreaterthan',
    'broadcast': 'event_broadcast',
    'broadcast_and_wait': 'event_broadcastandwait',
    # 运动
    'move_steps': 'motion_movesteps',
    'movesteps': 'motion_movesteps',
    'turn_left': 'motion_turnleft',
    'turnleft': 'motion_turnleft',
    'turn_right': 'motion_turnright',
    'turnright': 'motion_turnright',
    'point_in_direction': 'motion_pointindirection',
    'point_towards': 'motion_pointtowards',
    'goto': 'motion_goto',
    'goto_xy': 'motion_gotoxy',
    'glide_to': 'motion_glideto',
    'glide_xy': 'motion_glidesecstoxy',
    'change_x': 'motion_changexby',
    'change_y': 'motion_changeyby',
    'set_x': 'motion_setx',
    'set_y': 'motion_sety',
    'if_on_edge_bounce': 'motion_ifonedgebounce',
    'set_rotation_style': 'motion_setrotationstyle',
    'x_position': 'motion_xposition',
    'y_position': 'motion_yposition',
    'direction': 'motion_direction',
    # 外观
    'say': 'looks_sayforsecs',
    'sayforsecs': 'looks_sayforsecs',
    'say_no_wait': 'looks_say',
    'think': 'looks_thinkforsecs',
    'thinkforsecs': 'looks_thinkforsecs',
    'think_no_wait': 'looks_think',
    'switch_costume': 'looks_switchcostumeto',
    'next_costume': 'looks_nextcostume',
    'switch_backdrop': 'looks_switchbackdropto',
    'next_backdrop': 'looks_nextbackdrop',
    'change_effect': 'looks_changeeffectby',
    'set_effect': 'looks_seteffectto',
    'clear_effects': 'looks_cleargraphiceffects',
    'change_size': 'looks_changesizeby',
    'set_size': 'looks_setsizeto',
    'change_ghost_effect': 'looks_changeeffectby',
    'change_size_effect': 'looks_changesizeby',
    'go_to_front_back': 'looks_gotofrontback',
    'go_back_layers': 'looks_goforwardbackwardlayers',
    'go_to_front': 'looks_gotofrontback',
    'go_to_back': 'looks_gotofrontback',
    'show': 'looks_show',
    'hide': 'looks_hide',
    'costume_number_name': 'looks_costumenumbername',
    'backdrop_number_name': 'looks_backdropnumbername',
    # 声音
    'play_sound': 'sound_play',
    'start_sound': 'sound_play',
    'play_sound_until_done': 'sound_playuntildone',
    'stop_all_sounds': 'sound_stopallsounds',
    'change_sound_effect': 'sound_changeeffectby',
    'set_sound_effect': 'sound_seteffectto',
    'clear_sound_effects': 'sound_cleareffects',
    'change_volume': 'sound_changevolumeby',
    'set_volume': 'sound_setvolumeto',
    'volume': 'sound_volume',
    # 控制
    'wait': 'control_wait',
    'wait_until': 'control_wait_until',
    'repeat': 'control_repeat',
    'repeat_until': 'control_repeat_until',
    'while': 'control_while',
    'forever': 'control_forever',
    'if': 'control_if',
    'if_else': 'control_if_else',
    'stop': 'control_stop',
    'when_start_as_clone': 'control_start_as_clone',
    'create_clone_of': 'control_create_clone_of',
    'create_clone': 'control_create_clone_of',
    'delete_this_clone': 'control_delete_this_clone',
    # 侦测
    'touching': 'sensing_touchingobject',
    'touching_color': 'sensing_touchingcolor',
    'color_touching_color': 'sensing_coloristouchingcolor',
    'touching_mouse_pointer': 'sensing_touchingobject',
    'touchingmousepointer': 'sensing_touchingobject',
    'ask_and_wait': 'sensing_askandwait',
    'ask': 'sensing_askandwait',
    'answer': 'sensing_answer',
    'key_pressed': 'sensing_keypressed',
    'distance_to': 'sensing_distanceto',
    'distance': 'sensing_distanceto',
    'mousedown': 'sensing_mousedown',
    'mouse_x': 'sensing_mousex',
    'mouse_y': 'sensing_mousey',
    'set_drag_mode': 'sensing_setdragmode',
    'timer': 'sensing_timer',
    'reset_timer': 'sensing_resettimer',
    'of': 'sensing_of',
    'current': 'sensing_current',
    'days_since_2000': 'sensing_dayssince2000',
    'username': 'sensing_username',
    'loudness': 'sensing_loudness',
    # 运算
    'add': 'operator_add',
    'subtract': 'operator_subtract',
    'multiply': 'operator_multiply',
    'divide': 'operator_divide',
    'random': 'operator_random',
    'greater_than': 'operator_gt',
    'less_than': 'operator_lt',
    'equals': 'operator_equals',
    'and': 'operator_and',
    'or': 'operator_or',
    'not': 'operator_not',
    'join': 'operator_join',
    'letter_of': 'operator_letter_of',
    'length_of': 'operator_length',
    'contains': 'operator_contains',
    'mod': 'operator_mod',
    'round': 'operator_round',
    'mathop': 'operator_mathop',
    # 变量 / 列表
    'set_variable': 'data_setvariableto',
    'setvariableto': 'data_setvariableto',
    'change_variable': 'data_changevariableby',
    'changevariableby': 'data_changevariableby',
    'show_variable': 'data_showvariable',
    'hide_variable': 'data_hidevariable',
    'var': 'data_variable',
    'variable': 'data_variable',
    'add_to_list': 'data_addtolist',
    'delete_of_list': 'data_deleteoflist',
    'delete_all_of_list': 'data_deletealloflist',
    'insert_at_list': 'data_insertatlist',
    'replace_item_of_list': 'data_replaceitemoflist',
    'item_of_list': 'data_itemoflist',
    'item_num_of_list': 'data_itemnumoflist',
    'length_of_list': 'data_lengthoflist',
    'list_contains': 'data_listcontainsitem',
    'show_list': 'data_showlist',
    'hide_list': 'data_hidelist',
    'list': 'data_listcontents',
    'listcontents': 'data_listcontents',
    # 画笔
    'pen_down': 'pen_penDown',
    'pendown': 'pen_penDown',
    'pen_up': 'pen_penUp',
    'penup': 'pen_penUp',
    'pen_stamp': 'pen_stamp',
    'pen_clear': 'pen_clear',
    'set_pen_size': 'pen_setPenSizeTo',
    'change_pen_size': 'pen_changePenSizeBy',
    'set_pen_color': 'pen_setPenColorToColor',
    'change_pen_hue': 'pen_changePenHueBy',
    'set_pen_hue': 'pen_setPenHueToNumber',
    'change_pen_shade': 'pen_changePenShadeBy',
    'set_pen_shade': 'pen_setPenShadeToNumber',
    # 自定义积木
    'call': 'procedures_call',
    'call_proc': 'procedures_call',
    # 历史 opcode 别名（Scratch 3.0 早期命名，保持向后兼容）
    'looks_seteffect': 'looks_seteffectto',
    'looks_setsize': 'looks_setsizeto',
    'looks_gobacklayers': 'looks_goforwardbackwardlayers',
    'sound_seteffect': 'sound_seteffectto',
    'sound_setvolume': 'sound_setvolumeto',
}

# ---- 输入别名：IR 里可用的短键名 -> spec 里的输入名 ----
INPUT_ALIASES = {
    'control_if': {'cond': 'CONDITION', 'condition': 'CONDITION'},
    'control_if_else': {'cond': 'CONDITION', 'condition': 'CONDITION'},
    'control_repeat_until': {'cond': 'CONDITION', 'condition': 'CONDITION'},
    'control_while': {'cond': 'CONDITION', 'condition': 'CONDITION'},
    'control_wait_until': {'cond': 'CONDITION', 'condition': 'CONDITION'},
    'control_repeat': {'times': 'TIMES'},
    'control_wait': {'secs': 'DURATION', 'duration': 'DURATION'},
    'control_create_clone_of': {'clone': 'CLONE_OPTION'},
    'control_start_as_clone': {'clone': 'CLONE_OPTION'},
    'motion_movesteps': {'steps': 'STEPS'},
    'motion_gotoxy': {'x': 'X', 'y': 'Y'},
    'motion_glidesecstoxy': {'secs': 'SECS', 'x': 'X', 'y': 'Y'},
    'motion_glideto': {'secs': 'SECS'},
    'motion_changexby': {'dx': 'DX'},
    'motion_changeyby': {'dy': 'DY'},
    'motion_setx': {'x': 'X'},
    'motion_sety': {'y': 'Y'},
    'motion_turnright': {'degrees': 'DEGREES'},
    'motion_turnleft': {'degrees': 'DEGREES'},
    'motion_pointindirection': {'direction': 'DIRECTION'},
    'looks_sayforsecs': {'text': 'MESSAGE', 'secs': 'SECS', 'message': 'MESSAGE'},
    'looks_say': {'text': 'MESSAGE', 'message': 'MESSAGE'},
    'looks_thinkforsecs': {'text': 'MESSAGE', 'secs': 'SECS', 'message': 'MESSAGE'},
    'looks_think': {'text': 'MESSAGE', 'message': 'MESSAGE'},
    'looks_seteffectto': {'effect': 'EFFECT', 'value': 'VALUE'},
    'looks_changeeffectby': {'effect': 'EFFECT', 'value': 'CHANGE'},
    'looks_changesizeby': {'value': 'CHANGE', 'size': 'CHANGE', 'percent': 'CHANGE', 'by': 'CHANGE'},
    'looks_setsizeto': {'value': 'SIZE'},
    'looks_gotofrontback': {'front_back': 'FRONT_BACK'},
    'looks_goforwardbackwardlayers': {'forward_backward': 'FORWARD_BACKWARD', 'layers': 'NUM'},
    'looks_switchcostumeto': {'costume': 'COSTUME'},
    'looks_switchbackdropto': {'backdrop': 'BACKDROP'},
    'sound_play': {'sound': 'SOUND_MENU'},
    'sound_playuntildone': {'sound': 'SOUND_MENU'},
    'sound_seteffectto': {'effect': 'EFFECT', 'value': 'VALUE'},
    'sound_changeeffectby': {'effect': 'EFFECT', 'value': 'VALUE'},
    'sound_changevolumeby': {'value': 'VOLUME'},
    'sound_setvolumeto': {'value': 'VOLUME'},
    'sensing_askandwait': {'question': 'QUESTION'},
    'sensing_distanceto': {'object': 'DISTANCETOMENU'},
    'sensing_touchingobject': {'object': 'TOUCHINGOBJECTMENU'},
    'sensing_keypressed': {'key': 'KEY_OPTION'},
    'sensing_of': {'object': 'OBJECT', 'property': 'PROPERTY'},
    'operator_add': {'a': 'NUM1', 'b': 'NUM2'},
    'operator_subtract': {'a': 'NUM1', 'b': 'NUM2'},
    'operator_multiply': {'a': 'NUM1', 'b': 'NUM2'},
    'operator_divide': {'a': 'NUM1', 'b': 'NUM2'},
    'operator_gt': {'a': 'OPERAND1', 'b': 'OPERAND2'},
    'operator_lt': {'a': 'OPERAND1', 'b': 'OPERAND2'},
    'operator_equals': {'a': 'OPERAND1', 'b': 'OPERAND2'},
    'operator_and': {'a': 'OPERAND1', 'b': 'OPERAND2'},
    'operator_or': {'a': 'OPERAND1', 'b': 'OPERAND2'},
    'operator_not': {'operand': 'OPERAND'},
    'operator_join': {'a': 'STRING1', 'b': 'STRING2'},
    'operator_letter_of': {'letter': 'LETTER', 'word': 'STRING'},
    'operator_length': {'string': 'STRING'},
    'operator_contains': {'a': 'STRING1', 'b': 'STRING2'},
    'operator_mod': {'a': 'NUM1', 'b': 'NUM2'},
    'operator_random': {'from': 'FROM', 'to': 'TO'},
    'operator_mathop': {'n': 'NUM', 'num': 'NUM', 'value': 'NUM', 'op': 'OPERATOR'},
    'data_setvariableto': {'value': 'VALUE', 'to': 'VALUE'},
    'data_changevariableby': {'value': 'VALUE', 'by': 'VALUE'},
    'data_addtolist': {'item': 'ITEM'},
    'data_insertatlist': {'item': 'ITEM', 'index': 'INDEX'},
    'data_replaceitemoflist': {'item': 'ITEM', 'index': 'INDEX'},
    'data_deleteoflist': {'index': 'INDEX'},
    'data_itemoflist': {'index': 'INDEX'},
    'data_itemnumoflist': {'item': 'ITEM'},
    'data_listcontainsitem': {'item': 'ITEM'},
    'event_whenbroadcastreceived': {'message': 'BROADCAST_OPTION'},
    'event_broadcast': {'message': 'BROADCAST_INPUT'},
    'event_broadcastandwait': {'message': 'BROADCAST_INPUT'},
    'event_whenkeypressed': {'key': 'KEY_OPTION'},
    'event_whenbackdropswitchesto': {'backdrop': 'BACKDROP'},
    'music_playDrumForBeats': {'drum': 'DRUM', 'beats': 'BEATS'},
    'music_playNoteForBeats': {'note': 'NOTE', 'beats': 'BEATS'},
    'music_setInstrument': {'instrument': 'INSTRUMENT'},
    'music_setTempo': {'tempo': 'TEMPO'},
    'music_changeTempo': {'tempo': 'TEMPO'},
    'music_restForBeats': {'beats': 'BEATS'},
    'text2speech_speakAndWait': {'words': 'WORDS'},
    'text2speech_setVoice': {'voice': 'VOICE'},
    'text2speech_setLanguage': {'language': 'LANGUAGE'},
    'translate_getTranslate': {'words': 'WORDS', 'language': 'LANGUAGE'},
    'videoSensing_videoToggle': {'video_state': 'VIDEO_STATE'},
    'videoSensing_setVideoTransparency': {'transparency': 'TRANSPARENCY'},
    'videoSensing_videoOn': {'attribute': 'ATTRIBUTE', 'subject': 'SUBJECT'},
    'videoSensing_whenMotionGreaterThan': {'reference': 'REFERENCE', 'motion': 'MOTION'},
    'speech2text_whenIHearHat': {'phrase': 'PHRASE'},
    'pen_setPenSizeTo': {'size': 'SIZE'},
    'pen_changePenSizeBy': {'size': 'SIZE'},
    'pen_setPenColorToColor': {'color': 'COLOR'},
    'pen_setPenHueToNumber': {'hue': 'HUE'},
    'pen_changePenHueBy': {'hue': 'HUE'},
    'pen_setPenShadeToNumber': {'shade': 'SHADE'},
    'pen_changePenShadeBy': {'shade': 'SHADE'},
}


def camel_to_snake(name):
    s = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', name)
    s = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', s)
    return s.lower()


def main():
    with open(SPEC, encoding='utf-8') as f:
        spec = json.load(f)
    blocks = spec['blocks']

    aliases = {}
    for friendly, opcode in MANUAL.items():
        if opcode not in blocks:
            print('跳过（opcode 不存在）: %s -> %s' % (friendly, opcode), file=sys.stderr)
            continue
        aliases[friendly] = opcode

    # 自动别名：opcode 本身 + 下划线化形式
    for opcode in blocks:
        if blocks[opcode].get('shape') == 'menu-source':
            continue
        aliases.setdefault(opcode, opcode)
        snake = camel_to_snake(opcode)
        aliases.setdefault(snake, opcode)
        # 去掉类别前缀的形式，例如 motion_movesteps -> movesteps
        for cat in ('motion_', 'looks_', 'sound_', 'control_', 'sensing_',
                    'operator_', 'data_', 'event_', 'pen_', 'music_',
                    'text2speech_', 'translate_', 'videoSensing_'):
            if opcode.startswith(cat):
                aliases.setdefault(opcode[len(cat):], opcode)
                break

    # 同一 opcode 的多个别名指向同一 target，无需去重（dict 天然合并）
    out = {
        '$comment': '积木友好名 -> 原始 opcode。由 scripts/make_aliases.py 生成，'
                    '手工别名见该脚本的 MANUAL 字典。',
        'aliases': aliases,
        'input_aliases': INPUT_ALIASES,
    }
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print('写入 %s：别名 %d 条，输入别名 %d 条' % (OUT, len(aliases), len(INPUT_ALIASES)))


if __name__ == '__main__':
    main()
