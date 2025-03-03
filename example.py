from rs274_parser.dialects.linuxcnc import LinuxCNC, MachineState

initial_machine_state = MachineState(initial_named_parameter_values={"defined": 10, "param": 1})
parser = LinuxCNC(initial_machine_state)

gcode = """\
#<named_var> = 1
#1 = 0
#1 = 1 G0 X#1 Y#<named_var> (silly but legal) #1 = 2 ; will evaluate to G0 X0 Y1
G[#[#1-sin[90]]] X[1 * 1/1 - 1 ** 1 + LN[1]] ; will evaluate to G0 X0

"""
lines = parser.parse(gcode)

for line in lines:
    print(line)
