GRAMMAR = r"""
## LinuxCNC dialect of RS274/NGC, see http://linuxcnc.org/docs/stable/html/gcode/rs274ngc.html
## The linked documented does not mention semicolon comments, but this grammar includes them.
line < block_delete_character? line_number? (word / comment / parameter_setting / named_parameter_setting )* semicolon_comment? EndOfFile

EndOfFile  <- !.

unary_operator < ~([aA][bB][Ss] / [aA][cC][oO][sS] / [aA][sS][iI][nN] / [aA][tT][aA][nN] / [cC][oO][sS] / [eE][xX][pP] / [fF][iI][xX] / [fF][uU][pP] / [lL][nN] / [rR][oO][uU][nN][dD] / [sS][iI][nN] / [sS][qQ][rR][tT] / [tT][aA][nN])
l1_operator < ~("+" / "-" / [aA][nN][dD] / [oO][rR] / [xX][oO][rR])
l2_operator < ~("*" / "/")
l3_operator < ~("**")

comment < [(] ~(![)] . )* [)]

semicolon_comment < ";" ~(.*) EndOfFile

block_delete_character <- ~("/")
parameter_setting < "#" integer "=" real_value
named_parameter_setting < "#<" ~(![>] .)+ ">" "=" real_value
line_number < "N" integer
word < ~([a-zA-Z]) word_number

## An expression that evaluates to a number
real_value <- (number / expression / parameter_value / unary_operation)

word_number < ~("+" / "-")? real_value

## Named parameters are the main difference to the base rs274 spec
parameter_value <- numeric_parameter / named_parameter
numeric_parameter < "#" (integer / expression)
named_parameter < "#<" ~(![>] .)+ ">"

expression < "[" l1_operation "]"

unary_operation < unary_operator expression
l1_operation < l2_operation (l1_operator l2_operation)*
l2_operation < l3_operation (l2_operator l3_operation)*
l3_operation < operand (l3_operator operand)*
operand < ~("+" / "-")? real_value

number <- float / integer
integer < ~("-"?[0-9 \t]+)
float < ~("-"?[0-9 \t]*"."[0-9 \t]+)
"""
