GRAMMAR = r"""
## RS274NGC as per https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=823374
## (Or as close as I can get it)
line < block_delete_character? line_number? (word / parameter_setting / comment)* EndOfFile

EndOfFile  <- !.

unary_operator < ~([aA][bB][Ss] / [aA][cC][oO][sS] / [aA][sS][iI][nN] / [aA][tT][aA][nN] / [cC][oO][sS] / [eE][xX][pP] / [fF][iI][xX] / [fF][uU][pP] / [lL][nN] / [rR][oO][uU][nN][dD] / [sS][iI][nN] / [sS][qQ][rR][tT] / [tT][aA][nN])
l1_operator < ~("+" / "-" / [aA][nN][dD] / [oO][rR] / [xX][oO][rR])
l2_operator < ~("*" / "/")
l3_operator < ~("**")

comment < [(] ~(![)] . )* [)]

block_delete_character <- ~("/")
parameter_setting < "#" integer "=" real_value
line_number < "N" integer
word < ~([a-zA-Z]) word_number

## An expression that evaluates to a number
real_value <- (expression / numeric_parameter / unary_operation / number)

word_number < ~("+" / "-")? real_value

numeric_parameter < "#" (integer / expression)
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
