class_name GameApi
extends Node

const BASE_URL := "http://127.0.0.1:8000"

signal i18n_received(data: Dictionary)
signal player_received(data: Dictionary)
signal player_created(data: Dictionary)
signal player_allocated(data: Dictionary)
signal world_state_received(data: Dictionary)
signal npc_list_received(data: Array)
signal npc_detail_received(data: Dictionary)
signal npc_items_received(data: Array)
signal dialogue_received(data: Dictionary)
signal event_triggered(data: Dictionary)
signal event_list_received(data: Array)
signal event_resolved(data: Dictionary)
signal relationships_received(data: Array)
signal reward_list_received(data: Array)
signal item_list_received(data: Array)
signal item_action_done(action: String, data: Dictionary)
signal map_received(data: Dictionary)
signal chronicle_list_received(data: Array)
signal chronicle_generated(data: Dictionary)
signal request_failed(endpoint: String, error: String)


func fetch_i18n() -> void: _request("GET", "/i18n", {}, "i18n_received")
func fetch_player() -> void: _request("GET", "/player", {}, "player_received")

func create_player(pname: String, gender: String, background: String) -> void:
	_request("POST", "/player",
		{"name": pname, "gender": gender, "background": background},
		"player_created")

func allocate_point(attribute: String, count: int = 1) -> void:
	_request("POST", "/player/allocate",
		{"attribute": attribute, "count": count}, "player_allocated")

signal explore_done(data: Dictionary)

func explore() -> void:
	_request("POST", "/explore", {}, "explore_done")

signal action_done(data: Dictionary)

func do_action(action_name: String) -> void:
	_request("POST", "/action", {"action": action_name}, "action_done")

signal travel_done(data: Dictionary)

func travel(location_id: String) -> void:
	_request("POST", "/travel", {"location_id": location_id}, "travel_done")

func fetch_world_state() -> void: _request("GET", "/world/state", {}, "world_state_received")
func step_world() -> void: _request("POST", "/world/step", {}, "event_triggered")
func trigger_event() -> void: _request("POST", "/event/trigger", {}, "event_triggered")
func fetch_npcs() -> void: _request("GET", "/npc", {}, "npc_list_received")
func fetch_npc_detail(npc_id: String) -> void: _request("GET", "/npc/%s" % npc_id, {}, "npc_detail_received")
func fetch_relationships(npc_id: String) -> void: _request("GET", "/npc/%s/relationships" % npc_id, {}, "relationships_received")
func fetch_npc_items(npc_id: String) -> void: _request("GET", "/npc/%s/items" % npc_id, {}, "npc_items_received")

func send_dialogue(npc_id: String, player_input: String) -> void:
	_request("POST", "/npc/%s/dialogue" % npc_id, {"player_input": player_input}, "dialogue_received")

func fetch_events(limit: int = 20) -> void: _request("GET", "/event?limit=%d" % limit, {}, "event_list_received")
func fetch_rewards(limit: int = 20) -> void: _request("GET", "/reward?limit=%d" % limit, {}, "reward_list_received")
func fetch_items(limit: int = 100) -> void: _request("GET", "/item?limit=%d" % limit, {}, "item_list_received")
func fetch_map() -> void: _request("GET", "/map", {}, "map_received")
func fetch_chronicles(limit: int = 20) -> void: _request("GET", "/chronicle?limit=%d" % limit, {}, "chronicle_list_received")

func generate_chronicle(title_hint: String = "") -> void:
	_request("POST", "/chronicle/generate", {"title_hint": title_hint}, "chronicle_generated")

func take_item(item_id: String) -> void: _item_request("POST", "/item/%s/take" % item_id, {}, "take")
func drop_item(item_id: String) -> void: _item_request("POST", "/item/%s/drop" % item_id, {}, "drop")

func give_item(item_id: String, owner_id: String) -> void:
	_item_request("POST", "/item/%s/give" % item_id, {"owner_id": owner_id}, "give")

func use_item(item_id: String, target_npc_id: String) -> void:
	_item_request("POST", "/item/%s/use" % item_id, {"target_npc_id": target_npc_id}, "use")

func resolve_event(event_id: String, choice_id: String) -> void:
	_request("POST", "/event/%s/resolve" % event_id, {"choice_id": choice_id}, "event_resolved")


func _item_request(method: String, path: String, body: Dictionary, action_name: String) -> void:
	var http := HTTPRequest.new()
	http.timeout = 180.0
	add_child(http)
	http.request_completed.connect(_on_item_response.bind(http, action_name))
	var url := BASE_URL + path
	var headers := PackedStringArray(["Content-Type: application/json"])
	var err: int
	if method == "GET":
		err = http.request(url, headers, HTTPClient.METHOD_GET)
	else:
		err = http.request(url, headers, HTTPClient.METHOD_POST, JSON.stringify(body))
	if err != OK:
		http.queue_free()
		request_failed.emit(action_name, "request failed: %d" % err)


func _on_item_response(
	result: int, response_code: int,
	_headers: PackedStringArray, body: PackedByteArray,
	http: HTTPRequest, action_name: String
) -> void:
	http.queue_free()
	if result != HTTPRequest.RESULT_SUCCESS:
		request_failed.emit(action_name, "transport error")
		return
	var text := body.get_string_from_utf8()
	var data: Variant = JSON.parse_string(text)
	if response_code < 200 or response_code >= 300:
		var msg := "HTTP %d" % response_code
		if data is Dictionary and data.has("detail"):
			msg += ": " + str(data["detail"])
		request_failed.emit(action_name, msg)
		return
	item_action_done.emit(action_name, data if data is Dictionary else {})


func _request(method: String, path: String, body: Dictionary, signal_name: String) -> void:
	var http := HTTPRequest.new()
	http.timeout = 180.0
	add_child(http)
	http.request_completed.connect(_on_response.bind(http, signal_name))
	var url := BASE_URL + path
	var headers := PackedStringArray([
		"Content-Type: application/json",
		"Accept: application/json",
	])
	var err: int
	if method == "GET":
		err = http.request(url, headers, HTTPClient.METHOD_GET)
	else:
		err = http.request(url, headers, HTTPClient.METHOD_POST, JSON.stringify(body))
	if err != OK:
		http.queue_free()
		request_failed.emit(signal_name, "request failed: %d" % err)


func _on_response(
	result: int, response_code: int,
	_headers: PackedStringArray, body: PackedByteArray,
	http: HTTPRequest, signal_name: String
) -> void:
	http.queue_free()
	if result != HTTPRequest.RESULT_SUCCESS:
		request_failed.emit(signal_name, "transport error: %d" % result)
		return
	var text := body.get_string_from_utf8()
	var data: Variant = JSON.parse_string(text)
	if response_code < 200 or response_code >= 300:
		var msg := "HTTP %d" % response_code
		if data is Dictionary and data.has("detail"):
			msg += ": " + str(data["detail"])
		request_failed.emit(signal_name, msg)
		return
	if data == null:
		request_failed.emit(signal_name, "JSON parse failed")
		return
	emit_signal(signal_name, data)
