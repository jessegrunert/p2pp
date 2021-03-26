__author__ = 'Tom Van den Eede'
__copyright__ = 'Copyright 2018-2021, Palette2 Splicer Post Processing Project'
__credits__ = ['Tom Van den Eede',
               'Tim Brookman'
               ]
__license__ = 'GPLv3'
__maintainer__ = 'Tom Van den Eede'
__email__ = 'P2PP@pandora.be'

import p2pp.purgetower as purgetower
import p2pp.variables as v
from p2pp.gcode import issue_code
import p2pp.manualswap as swap


#
# to be implemented - Big Brain 3D purge mechanism support
#

def setfanspeed(n):
    if n == 0:
        issue_code("M107                ; Turn FAN OFF")
    else:
        issue_code("M106 S{}           ; Set FAN Power".format(n))


def resetfanspeed():
    setfanspeed(v.saved_fanspeed)


def generate_blob(length, count):
    issue_code("\n;---- BIGBRAIN3D SIDEWIPE BLOB {} -- purge {:.3f}mm".format(count + 1, length), True)
    # issue_code("M907 X{} ; set motor power\n".format(int(v.purgemotorpower)))

    setfanspeed(0)
    if v.bigbrain3d_fanoffdelay > 0:
        issue_code("G4 P{} ; delay to let the fan spinn down".format(v.bigbrain3d_fanoffdelay))

    issue_code(
        "G1 X{:.3f} F3000   ; go near the edge of the print".format(v.bigbrain3d_x_position - v.bigbrain3d_left * 10))
    issue_code(
        "G1 X{:.3f} F1000   ; go to the actual wiping position".format(v.bigbrain3d_x_position))  # takes 2.5 seconds

    if v.retraction < 0:
        purgetower.unretract(v.current_tool, 1200)
    if v.bigbrain3d_smartfan:
        issue_code("G1 E{:6.3f} F{}     ; Purge FAN OFF ".format(length / 4, v.bigbrain3d_blob_speed))
        setfanspeed(32)
        issue_code("G1 E{:6.3f} F{}     ; Purge FAN 12% ".format(length / 4, v.bigbrain3d_blob_speed))
        setfanspeed(64)
        issue_code("G1 E{:6.3f} F{}     ; Purge FAN 25% ".format(length / 4, v.bigbrain3d_blob_speed))
        setfanspeed(96)
        issue_code("G1 E{:6.3f} F{}     ; Purge FAN 37% ".format(length / 4, v.bigbrain3d_blob_speed))
    else:
        issue_code("G1 E{:6.3f} F{}     ; UNRETRACT/PURGE/RETRACT ".format(length, v.bigbrain3d_blob_speed))
    purgetower.largeretract()
    setfanspeed(255)
    issue_code(
        "G4 S{0:.0f}              ; blob {0}s cooling time".format(v.bigbrain3d_blob_cooling_time))
    issue_code("G1 X{:.3f} F10800  ; activate flicker".format(v.bigbrain3d_x_position - v.bigbrain3d_left * 20))

    for i in range(v.bigbrain3d_whacks):
        issue_code(
            "G4 S1               ; Mentally prep for second whack".format(v.bigbrain3d_x_position - v.bigbrain3d_left * 20))
        issue_code("G1 X{:.3f} F3000   ; approach for second whach".format(v.bigbrain3d_x_position - v.bigbrain3d_left * 10))
        issue_code("G1 X{:.3f} F1000   ; final position for whack and......".format(
            v.bigbrain3d_x_position))  # takes 2.5 seconds
        issue_code("G1 X{:.3f} F10800  ; WHACKAAAAA!!!!".format(v.bigbrain3d_x_position - v.bigbrain3d_left * 20))


def create_sidewipe_bb3d(length):

    # purge blobs should all be same size
    purgeleft = length % v.bigbrain3d_blob_size
    purgeblobs = int(length / v.bigbrain3d_blob_size)

    if purgeleft > 1:
        purgeblobs += 1

    correction = v.bigbrain3d_blob_size * purgeblobs - length

    issue_code(";-------------------------------", True)
    issue_code("; P2PP BB3DBLOBS: {:.0f} BLOBS".format(purgeblobs), True)
    issue_code(";-------------------------------", True)

    issue_code(
        "; Req={:.2f}mm  Act={:.2f}mm".format(length, length + correction))
    issue_code("; Purge difference {:.2f}mm".format(correction))
    issue_code(";-------------------------------")

    if v.retraction == 0:
        purgetower.largeretract()

    keep_xpos = v.current_position_x
    keep_ypos = v.current_position_y

    if v.current_position_z < v.bigbrain3d_minimalclearenceheight:
        issue_code("\nG1 Z{:.3f} F8640    ; Increase Z to prevent collission with bed".format(v.bigbrain3d_minimalclearenceheight))

    if v.bigbrain3d_y_position is not None:
        issue_code("\nG1 Y{:.3f} F8640    ; change Y position to purge equipment".format(v.bigbrain3d_y_position))

    issue_code("G1 X{:.3f} F10800  ; go near edge of bed".format(v.bigbrain3d_x_position - 30))

    if v.manual_filament_swap:
        swap.swap_pause("M25")
        swap.swap_unpause()

    issue_code("G4 S0               ; wait for the print buffer to clear")
    v.processed_gcode.append("M907 X{}           ; increase motor power".format(v.bigbrain3d_motorpower_high))
    issue_code("; -- P2PP -- Generating {} blobs for {}mm of purge".format(purgeblobs, length), True)

    for i in range(purgeblobs):
        generate_blob(v.bigbrain3d_blob_size, i)

    if v.current_position_z < v.bigbrain3d_minimalclearenceheight:

        if v.retraction != 0:
            purgetower.retract(v.current_tool)

        issue_code("\nG1 X{:.3f} Y{:.3f} F8640".format(keep_xpos, keep_ypos))
        issue_code("\nG1 Z{:.4f} F8640    ; Reset correct Z height to continue print".format(v.current_position_z))

    resetfanspeed()
    v.processed_gcode.append("\nM907 X{}           ; reset motor power".format(v.bigbrain3d_motorpower_normal))
    issue_code("\n;-------------------------------\n", True)


def create_side_wipe(length=0):

    if length != 0:
        v.side_wipe_length = length

    if not v.side_wipe or v.side_wipe_length == 0:
        return

    if v.bigbrain3d_purge_enabled:
        create_sidewipe_bb3d(v.side_wipe_length)
        v.side_wipe_length = 0
    else:

        issue_code(";---------------------------", True)
        issue_code(";  P2PP SIDE WIPE: {:7.3f}mm".format(v.side_wipe_length), True)

        for line in v.before_sidewipe_gcode:
            issue_code(line)

        if v.retraction == 0:
            purgetower.retract(v.current_tool)

        issue_code("G1 F8640")
        issue_code("G1 {} Y{}".format(v.side_wipe_loc, v.sidewipe_miny))

        if v.manual_filament_swap:
            swap.swap_pause("M25")
            swap.swap_unpause()

        delta_y = abs(v.sidewipe_maxy - v.sidewipe_miny)

        if v.sidewipe_maxy == v.sidewipe_miny:      # no Y movement, just purge

            while v.side_wipe_length > 0:
                sweep = min(v.side_wipe_length, 50)
                issue_code("G1 E{:.5f} F{}".format(sweep, v.wipe_feedrate))
                purgetower.largeretract()  # 3mm retraction cycle to dislodge potential stuck filament
                purgetower.unretract(v.current_tool, v.wipe_feedrate, "", True)
                v.side_wipe_length -= sweep

        else:

            sweep_base_speed = v.wipe_feedrate * 20 * delta_y / 150
            sweep_length = 20

            yrange = [v.sidewipe_maxy, v.sidewipe_miny]
            rangeidx = 0
            movefrom = v.sidewipe_miny
            moveto = yrange[rangeidx]
            numdiffs = 20
            purgetower.unretract(v.current_tool)

            while v.side_wipe_length > 0:
                sweep = min(v.side_wipe_length, sweep_length)
                v.side_wipe_length -= sweep_length
                wipe_speed = min(5000, int(sweep_base_speed / sweep))

                # split this move in very short moves to allow for faster planning buffer depletion
                diff = (moveto - movefrom) / numdiffs

                for i in range(numdiffs):
                    issue_code("G1 {} Y{:.3f} E{:.5f} F{}".format(v.side_wipe_loc, movefrom + (i+1)*diff, sweep/numdiffs * v.sidewipe_correction, wipe_speed))

                # issue_code(
                #     "G1 {} Y{} E{:.5f} F{}\n".format(v.side_wipe_loc, moveto, sweep * v.sidewipe_correction, wipe_speed))

                rangeidx += 1
                movefrom = moveto
                moveto = yrange[rangeidx % 2]

        for line in v.after_sidewipe_gcode:
            issue_code(line)

        purgetower.retract(v.current_tool)
        issue_code("G1 F8640")
        issue_code(";---------------------------", True)

        v.side_wipe_length = 0
