from beet import Context, Function

from camellia.utils import merge_func_tag

tick = "camellia:technical/tick"
second_clock = "camellia:technical/second_clock"
ten_second_clock = "camellia:technical/ten_second_clock"

def beet_default(ctx: Context):
	global tick, second_clock, ten_second_clock
	ns = ctx.project_id
	dir = f"{ns}:technical"

	# create function names
	tick = f"{dir}/tick"
	second_clock = f"{dir}/second_clock"
	ten_second_clock = f"{dir}/ten_second_clock"

	# append each function to the corresponding tag if it is within the config
	clock_config: dict = ctx.meta.get("camellia", {}).get("clocks", {})
	
	if clock_config.get("tick", False):
		ctx.data.functions[tick] = Function()
		merge_func_tag(ctx, "minecraft:tick", tick)
	
	if clock_config.get("second_clock", False):
		ctx.data.functions[second_clock] = Function(f"schedule function {second_clock} 1s replace")
		merge_func_tag(ctx, "minecraft:load", second_clock)

	if clock_config.get("ten_second_clock", False):
		ctx.data.functions[ten_second_clock] = Function(f"schedule function {ten_second_clock} 10s replace")
		merge_func_tag(ctx, "minecraft:load", ten_second_clock)
