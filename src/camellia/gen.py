import re
from collections import defaultdict

from beet import (
	Context,
	Enchantment,
	Function,
	FunctionTag,
	LootTable,
	Mcmeta,
	Recipe,
	SoundConfig,
)


def mcmeta(ctx: Context):
	dp = [107, 1]
	rp = [88, 0]

	ctx.data.mcmeta = Mcmeta({
		"id": ctx.project_id,
		"pack": {
			"description": ctx.project_description,
			"pack_format": dp[0],
			"min_format": dp,
			"max_format": dp,
		}
	})
	ctx.assets.mcmeta = Mcmeta({
		"id": ctx.project_id,
		"pack": {
			"description": ctx.project_description,
			"pack_format": rp[0],
			"min_format": rp[0],
			"max_format": rp[0],
		}
	})


def recipe_outputs(ctx: Context):
	"""Adds components to recipes from loot table entries of the same name"""
	ns = ctx.project_id

	for key, recipe in ctx.data.recipes.items():
		recipe_data = recipe.data
		loot_path = f"{ns}:items/{key.split(":")[1]}"

		if loot_path in ctx.data.loot_tables:
			loot_data = ctx.data.loot_tables[loot_path].data
			
			try:
				entry = loot_data["pools"][0]["entries"][0]
				components = entry["functions"][0]["components"]
				item_id = entry["name"]

				recipe_data.setdefault("result", {})["id"] = item_id
				recipe_data.setdefault("result", {})["components"] = components
				ctx.data.recipes[key] = Recipe(recipe_data)
			except (KeyError, IndexError):
				print(f"!> Failed to extract components from loot table: {loot_path}")


def uninstall_function(ctx: Context):
	"""Generates an uninstall command that removes scoreboards, teams, and schedules"""
	ns = ctx.project_id
	removes = []
	for func in ctx.data[ns].functions.values():
		for line in func.lines:
			if line.startswith("scoreboard objectives add"):
				parts = line.split()
				if len(parts) >= 3:
					removes.append(f"scoreboard objectives remove {parts[3]}")
			if line.startswith("team add"):
				parts = line.split()
				if len(parts) >= 3:
					removes.append(f"team remove {parts[2]}")
			if line.startswith("schedule function"):
				parts = line.split()
				if len(parts) >= 3:
					removes.append(f"schedule clear {parts[2]}")

	if len(removes) > 0:
		#removes.insert(0, "# Generated uninstall function")
		ctx.data.functions[f"{ns}:commands/uninstall"] = Function(removes)


def sounds_json(ctx: Context):
	"""Generates sounds.json by going through the sounds directory"""
	ns = ctx.project_id
	grouped_sounds = defaultdict(list)

	for sound in ctx.assets[ns].sounds:
		parts = sound.split('/')  # e.g., ['block', 'pitcher_plant', 'hurt1']
		filename = parts[-1]
		
		# This strips any trailing digits from the end of the filename
		base_name = re.sub(r'\d+$', '', filename)

		# Use dot notation for the key: e.g., block.pitcher_plant.hurt
		key_parts = parts[:-1] + [base_name]
		sound_key = ".".join(key_parts)
		
		# Add the full path to the group
		grouped_sounds[sound_key].append(f"{ns}:{'/'.join(parts)}")

	# Build the final sound config
	sound_dict = {}
	for sound_key, sound_paths in grouped_sounds.items():
		entry = {
			"sounds": sound_paths
		}
		
		# Add subtitle only if the sound event is not music
		if not sound_key.startswith("music"):
			entry["subtitle"] = f"subtitles.{ns}.{sound_key}"
			
		sound_dict[sound_key] = entry

	# Fetch the existing config
	existing_config = getattr(ctx.assets[ns], "sound_config", None)
	existing_sounds = {}

	if existing_config is not None:
		existing_sounds = existing_config.data

	# Merge logic: existing_sounds now OVERRIDES sound_dict
	# By placing **existing_sounds second, its keys overwrite any matches in sound_dict
	merged_sounds = {**sound_dict, **existing_sounds}
	
	ctx.assets[ns].sound_config = SoundConfig(merged_sounds)


def enchant_predicate_references(ctx: Context):
	"""Allows predicate references in enchantments by inserting the contents of the referenced predicate"""
	def resolve_references(obj):
		if isinstance(obj, dict):
			if obj.get("condition") == "minecraft:reference" and "name" in obj:
				ref_name = obj["name"]
				try:
					ref_file = ctx.data.predicates[ref_name]
					ref_data = ref_file.data
					return resolve_references(ref_data)
				except KeyError:
					print(f"!> Reference not found: {ref_name}")
					return obj
			else:
				return {k: resolve_references(v) for k, v in obj.items()}
		elif isinstance(obj, list):
			return [resolve_references(i) for i in obj]
		else:
			return obj

	for name, enchant in ctx.data.enchantments.items():
		enchant_data = enchant.data
		resolved = resolve_references(enchant_data)
		ctx.data.enchantments[name] = Enchantment(resolved)


def updater(ctx: Context):
	"""Generates a Thallium updater loot table from the pack's `items/` loot tables"""
	ns = ctx.project_id
	with ctx.generate.draft() as draft:
		draft.cache("updater", str(ctx.data[ns].loot_tables))
		updater_entries = []

		def make_inverted_condition(data):
			return {
				"condition": "minecraft:inverted",
				"term": {
					"condition": "minecraft:entity_properties",
					"entity": "this",
					"predicate": {"slots": {"contents": {"predicates": {"minecraft:custom_data": data}}}}
				}
			}

		def make_entry(value, contents=None, keep_count=False):
			conditions = []
			if contents:
				conditions.append({
					"condition": "minecraft:entity_properties",
					"entity": "this",
					"predicate": {"slots": {"contents": contents}}
				})
				if "items" in contents and "minecraft:custom_data" not in (contents.get("predicates") or {}):
					conditions.extend([
						make_inverted_condition({ns: {}}),
						make_inverted_condition({"smithed": {}})
					])
			entry = {"type": "minecraft:loot_table", "value": value, "conditions": conditions}

			if keep_count:
				entry["functions"] = [{
					"function": "minecraft:set_count",
					"count": {"type": "minecraft:score", "target": "this", "score": "thallium.dummy"}
				}]
			return entry

		# Auto-generate entries from loot_tables
		for key, loot_path in ctx.data[ns].loot_tables.items():
			if not key.startswith("items/"): 
				continue
			
			fk = f"{ns}:{key}"
			components = loot_path.data["pools"][0]["entries"][0]["functions"][0]["components"]
			if "minecraft:custom_data" not in components:
				continue
			
			item_id = components["minecraft:custom_data"][ns]["id"]
			keep_count = components.get("minecraft:max_stack_size", 2) != 1
			updater_entries.append(make_entry(fk, { "predicates": {"minecraft:custom_data":{ns:{"id":item_id}}} }, keep_count))

		loot_path = f"{ns}:technical/updater"
		func_path = f"{ns}:technical/updater/main"
		draft.data.loot_tables[loot_path] = LootTable({"pools": [{"entries": updater_entries, "rolls": 1.0}]})
		draft.data.functions[func_path] = Function([f"loot replace entity @s contents loot {loot_path}"])
		
		# Append to the function tag if it exists, or create it otherwise
		tag_name = "thallium:updater/main"
		tag_value = FunctionTag( {"values":[func_path]} )
		if tag_name in draft.data.function_tags:
			draft.data.function_tags[tag_name].append(tag_value)
		else:
			draft.data.function_tags[tag_name] = tag_value

		print("> Updater loot table built")


def copy_spanish(ctx: Context):
	ns = ctx.project_id
	langs = ["es_ar", "es_cl", "es_ec", "es_es", "es_uy", "es_ve"]
	for lang in langs:
		ctx.assets.languages[f"{ns}:{lang}"] = ctx.assets.languages[f"{ns}:es_mx"]
		mx = ctx.assets.languages.get("minecraft:es_mx")
		if mx:
			ctx.assets.languages[f"minecraft:{lang}"] = mx