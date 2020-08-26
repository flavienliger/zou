from zou.plugins.event_handlers import output_file_new, generate_children

event_map = {
    "output_file:new": output_file_new.handle_event,
    "children_file:new": generate_children.handle_event,
    "children-file:update": generate_children.handle_event
}