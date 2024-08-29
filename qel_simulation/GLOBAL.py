import pandas as pd

def convert_numeric_columns(df):
    df = df.apply(lambda col: pd.to_numeric(col, errors='ignore'))
    return df


EVENT_ID = "ocel_id"
TIMESTAMP = "ocel_time"
ACTIVITY = "ocel_type"
OBJECT_ID = "ocel_id"
OBJECT_TYPE = "ocel_type"
QTY_OPERATION = "ocel_object_qty_operation"
QUALIFIER = "ocel_qualifier"
O2O_SOURCE = "ocel_source_id"
O2O_TARGET = "ocel_target_id"
E2O_EVENT = "ocel_event_id"
E2O_OBJECT = "ocel_object_id"
COLLECTION_ID = "ocel_cpid"
OBJECT_CHANGE = "ocel_changed_field"
ACTIVITY_MAP = "ocel_type_map"
OBJECT_TYPE_MAP = "ocel_type_map"
TABLE_MAPPING_OBJECT = "object_map_type"
TABLE_MAPPING_EVENT = "event_map_type"
TABLE_OBJECT_QTY = "object_quantity"
TABLE_EVENT_OBJECT = "event_object"
TABLE_OBJECT_OBJECT = "object_object"
TABLE_EVENT = "event"
TABLE_EQTY = "quantity_operations"
TABLE_OBJECT = "object"
TABLE_ACTIVITY_PREFIX = "event_"
TABLE_OBJECT_PREFIX = "object_"
OBJECT_COLUMNS = [OBJECT_ID, OBJECT_TYPE, TIMESTAMP, OBJECT_CHANGE]


TERM_ACTIVE = "active"
TERM_INACTIVE = "inactive"
TERM_QOP = "quantity_operation"
TERM_INIT = "init"
TERM_END_TIME = "end_timestamp"
TERM_NAME = "name"
TERM_ID = "id"
TERM_TYPE = "type"
TERM_DATA = "data"
TERM_DIRECTION = "qty_direction"
TERM_ADDING_REMOVING = "both"

TERM_ADDING = "adding"
TERM_REMOVING = "removing"
TERM_EVENT_PERSPECTIVE = "event"
TERM_QUANTITY_UPDATE_PERSPECTIVE = "quantity_update"
TERM_QUANTITY_OPERATION_PERSPECTIVE = "quantity_operation"
TERM_COMPLETE = "complete"
TERM_ITEM_AGGREGATION = "item_aggregation"
TERM_COLLECTION = "Collection"
TERM_ACTIVITY = "Activity"
TERM_ACTIVITIES = TERM_ACTIVITY
TERM_EVENT = "Events"
TERM_EVENTS = TERM_EVENT
TERM_OBJECT = "Objects"
TERM_OBJECTS = TERM_OBJECT
TERM_OBJECT_TYPE = "Object Types"
TERM_QUANTITY_OPERATIONS = "Quantity Operations"
TERM_TIME = "Time"
TERM_ILVL = "Item_Level_Development"
TERM_ITEM_TYPES = "Item Types"
TERM_QTY_OBJECTS = "Quantity Objects"
TERM_QTY_OBJECT_TYPES = "Quantity Object Types"
TERM_QTY_EVENTS = "Quantity Events"
TERM_COLLECTIONS = TERM_COLLECTION

# terminology element overview
TERM_RELATED_EVENTS = "related events"
TERM_RELATED_QTY_OPERATIONS = "related quantity operations"
TERM_RELATED_QTY_EVENTS = "related quantity events"
TERM_QUANTITY_RELATIONS = "quantity relations"
TERM_QTY_ACTIVITIES = "q-activities"
TERM_RELATED_QTY_ACTIVITIES = "related quantity activities"
TERM_OBJECT_TYPES = "object types"
TERM_RELATED_OBJECT_TYPES = "related object types"
TERM_RELATED_OBJECTS = "related objects"
TERM_RELATED_ITEM_TYPES = "related item types"
TERM_RELATED_QTY_OBJECTS = "related quantity objects"
TERM_RELATED_QTY_OBJECT_TYPES = "related quantity object types"
TERM_RELATED_ACTIVITIES = "related activities"
TERM_LOG = "Event Log"
TERM_E2O = "Event to Object Relations"
TERM_ACTIVE_QOP = "Active Quantity Relations"
TERM_ITEM_LEVELS = "Item Levels"
TERM_ITEM_QUANTITY = "Item Quantities"
TERM_QUANTITY = "Quantity"
TERM_PROPERTY = "Property"
TERM_ALL = "All"
TERM_ANY = "Any"
TERM_NONE = "None"
TERM_FULLY_ADDING = "Fully Adding"
TERM_FULLY_REMOVING = "Fully Removing"
TERM_ITEM_TYPE_ACTIVE = "Item Type Active"
TERM_PERSPECTIVE = "Perspective"
TERM_ITEM_TYPES_SELECTED = "Selected Item Types"
TERM_QUANTITY_UPDATES: str = "Quantity Updates"
TERM_COMBINED = "Combined"
TERM_COMBINED_INSTANCES = "Combined Instances"

TERM_LAST_CHANGE = "last_change"
TERM_SELECTED_ELEMENT = "selected_element"
TERM_FILTER = "process_element_filter"
TERM_OBJECT_TYPE_COUNT = "object_count"
TERM_OBJECT_COUNT = "total_objects"
TERM_EXECUTION_COUNT = "Execution no."
TERM_INSTANCE_COUNT = "instance_count"
TERM_VIEW_ITEM_LEVELS = "View Item Levels"

EVENT_COUNT = "Event Count"
TERM_RELATIVE_FREQUENCY = "relative_frequency"
TERM_CP_ACTIVE = "collection point active"

SELECTION_COLLECTION = "Collection"
SELECTION_ACTIVITY = "Activity"
SELECTION_OBJECT_TYPE = "Object Type"
SELECTION_QR = "Quantity Relation"

QOP_FILTER_ALL = "ALL"
QOP_FILTER_ACTIVE = "ACTIVE"
QOP_FILTER_ADDING = "ADDING"
QOP_FILTER_REMOVING = "REMOVING"

TERM_ITEM_MOVEMENTS = "Material Movement"
TERM_QUANTITY_CHANGES = "Quantity Changes"
TERM_ILVL_ITEM_TYPE_AGGREGATION = "Item Level Item Type Aggregation"
ILVL_ITEM_TYPE_AGGREGATION_VALUE = "Item Level Item Type Aggregation Value"
TERM_ILVL_CP_AGGREGATION = "Item Level Collection Aggregation"
ILVL_CP_AGGREGATION_VALUE = "Item Level Collection Aggregation Value"
TERM_ACTIVE_OPERATIONS = "Active Quantity Operations"
TERM_ACTIVE_UPDATES = "Active Quantity Updates"

ITEM_LEVEL_TYPE = "Item Level Type"
POST_EVENT_ILVL = "Post Event Item Level"
PRE_EVENT_ILVL = "Pre Event Item Level"

EVENT_FILTER_ACTIVITY = "event_filter_activities"
EVENT_FILTER_OBJECT_TYPE = "event_filter_object_types"
EVENT_FILTER_OBJECT_COUNT = "event_filter_object_count"
EVENT_FILTER_OBJECT_TYPE_OBJECTS = "event_filter_object_type_objects"
EVENT_FILTER_COLLECTION_ACTIVE = "event_filter_collection_points_active"
EVENT_FILTER_OBJECT_TYPE_OBJECT_TYPE = "event_filter_object_type_object_type"
EVENT_FILTER_ITEM_TYPE_ACTIVE = "event_filter_item_type_active"
EVENT_FILTER_QEVENT = "event_filter_quantity_events"
EVENT_FILTER_EXECUTIONS_OBJECT_TYPE = "event_filter_executions_object_type"
EVENT_FILTER_EXECUTIONS = "event_filter_executions"
EVENT_FILTER_RECALCULATE = "event_filter_recalculate"
TERM_ITEM_ASSOCIATION = "Item Association"
ILVL_AVAILABLE = "Available"
ILVL_REQUIRED = "Required"

QOP_ID = "qop_id"
QOP_COUNT = "qop_count"
TERM_EVENT_DATA = "event_data"
TERM_OBJECT_DATA = "object_data"
TERM_OBJECT_TYPE_COMBINATION = "object type combinations"
TERM_OBJECT_TYPE_COMBINATION_FREQUENCY = "object type combination frequency"
TERM_SUBLOG = "Sublog"
TERM_COUNT = "Count"
TERM_DAILY = "Daily"
TERM_MONTHLY = "Monthly"
TERM_QUP_TYPE = "Quantity Update Type"


TERM_SUM = "Aggregation"
AGG_QTY = "Quantity"
AGG_ABS = "Items"
AGG_POSITIVE = "Positive"
AGG_NEGATIVE = "Negative"
AGG_ILVL_QTY = "Item Balance"
AGG_ILVL_ITEM = "Item Association"
AGG_ILVL_AVAILABLE = "Available Items"
AGG_ILVL_REQUIRED = "Required Items"
AGG_QOP_IT_BALANCE = "Total Quantity Balance"
AGG_QOP_IT_MOVEMENTS = "Total Item Moves"
AGG_QOP_IT_ADDING = "Total Added Items"
AGG_QOP_IT_REMOVING = "Total Removed Items"

QOP_AGG_CP = "Joint Quantity Data"
QOP_AGG_IT = "Total Quantity Balance"
QOP_AGG_CP_QTY = "Joint Quantity Operation"
QOP_AGG_CP_ABS = "Joint Item Movements"
TERM_VALUE = "Value"
TERM_OBJECT_ACTIVITY = "Object Activity"

TERM_AGG_CP = "Joint"
TERM_AGG_ITEM_TYPES = "Total"
TERM_AGG_EVENT = "Combined"

ILVL_CP_SELECTION = "Collection Points Quantity State"
QOP_CP_SELECTION = "Collection Points Quantity Changes"

ILVL_AGG_CP = "Aggregate Item Levels"
ILVL_AGG_CP_QTY_ASSOCIATIONS = "Joint Quantity Associations"
ILVL_AGG_CP_QTY_STATE = "Joint Quantity State"
ILVL_AGG_IT = "Aggregate Item Types"

EVENT_AGG_QTY = "Overall Quantity Operation"
EVENT_AGG_ABS = "Overall Item Movements"

TERM_TIME_SINCE_LAST_EXECUTION = "Time since last execution"

# ###### Defaults #######
# INITIAL_TIME = datetime.datetime(year=2019, month=10, day=12, hour=12, minute=21)

DEFAULT_STATE = {TERM_NAME: None, TERM_TYPE: None, TERM_LAST_CHANGE: None,
                 EVENT_FILTER_ACTIVITY: TERM_ALL, EVENT_FILTER_QEVENT: False,
                 EVENT_FILTER_OBJECT_TYPE: None, EVENT_FILTER_OBJECT_COUNT: None,
                 EVENT_FILTER_OBJECT_TYPE_OBJECTS: None, EVENT_FILTER_OBJECT_TYPE_OBJECT_TYPE: None, EVENT_FILTER_EXECUTIONS_OBJECT_TYPE: None, EVENT_FILTER_EXECUTIONS: None,
                 EVENT_FILTER_COLLECTION_ACTIVE: None,
                 EVENT_FILTER_ITEM_TYPE_ACTIVE: None,
                 EVENT_FILTER_RECALCULATE: True,
                 }

DEFAULT_ILVL_SETTING = {TERM_ITEM_TYPES: TERM_ALL,
                        ILVL_CP_SELECTION: TERM_ALL,
                        ITEM_LEVEL_TYPE: PRE_EVENT_ILVL,
                        TERM_ILVL_CP_AGGREGATION: TERM_NONE,
                        TERM_ILVL_ITEM_TYPE_AGGREGATION: TERM_NONE,
                        TERM_EVENTS: TERM_ALL
                        }

DEFAULT_QOP_SETTING = {TERM_PERSPECTIVE: TERM_QUANTITY_OPERATION_PERSPECTIVE,
                       TERM_PROPERTY: TERM_ALL,
                        QOP_CP_SELECTION: TERM_ALL,
                        QOP_AGG_IT: TERM_NONE,
                        QOP_AGG_CP: TERM_NONE,
                       TERM_ITEM_TYPES: TERM_ALL,
                       }

CHART_COLOURS = ["#006165", # petrol
                 "#CE108A", # pink
                 "#0098A1", # turquoise
                 "#F6A800", # orange
                "#00549F", # blue
                "#6f2b4b",# purple
                 "#8EBAE5", # light blue
                "#000080", # dark blue
                "#007e56", # lighter greeny-turquoise
                "#005d4c", # perl-ophal green
                "#a1dfd7", #light-turquoise
                "#cd00cd", # pink

                 "#28713e", # green
                 "#701f29", # purpur-red

                 "#5d2141", # other purple
                 "#a1dfd7", #light-turquoise

                "#00ffff", # cyan
                "#39ff14", # neon green
                 "#800080", #purpur
                "#005f6a", # blue-petrol
                "#76e1e0", # another turquopise
                "#f5ff00" # neon-yellow
                 ]
