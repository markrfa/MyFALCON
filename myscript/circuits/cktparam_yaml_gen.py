# TODO: 
# the current scheme using a single cktparam.yaml limits the parameter space that we explore
# for instance, an op-amp may have mosfets with varying width, length, and mn/mp 
# but my model assumes that those values are same for all mosfets
# 
# there should be a script that can identify what parameters can be varied
# by inspecting the netlists (.cir)
# and from there generate a yaml file that lists the parameters similar to what cktparam.yaml is doing
# (for the output yaml format, refer to cktparam.yaml)