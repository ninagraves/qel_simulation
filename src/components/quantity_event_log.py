import os
from collections import Counter
from itertools import product

import numpy as np
from sqlalchemy import create_engine

from src.components.base_element import BaseElement
from src.components.log_elements.event import Event
from src.components.log_elements.object import Object
from src.components.net_elements.collection_point import CollectionPoint
from src.GLOBAL import *
import datetime


class QuantityEventLog(BaseElement):

    def __init__(self, name=None, label: str = None, properties: dict = None, event_data: dict = None,
                 object_data: dict = None, e2o: pd.DataFrame = None, o2o: pd.DataFrame = None,
                 eqty: pd.DataFrame = None, event_map_type: pd.DataFrame = None, object_map_type: pd.DataFrame = None,
                 object_quantities: pd.DataFrame = None, **kwargs):

        super().__init__(name=name, label=label, properties=properties)

        self.object_id_col = OBJECT_ID
        self.event_id_col = EVENT_ID
        self.activity_col = ACTIVITY
        self.object_type_col = OBJECT_TYPE
        self.timestamp_col = TIMESTAMP
        self.collection_col = COLLECTION_ID
        self.object_change = OBJECT_CHANGE
        self.qualifier = QUALIFIER
        self.o2o_source = O2O_SOURCE
        self.o2o_target = O2O_TARGET
        self.activity_map = ACTIVITY_MAP
        self.object_map = OBJECT_TYPE_MAP
        self.e2o_event = E2O_EVENT
        self.e2o_object = E2O_OBJECT
        self.term_active = TERM_ACTIVE
        self.term_qop = TERM_QOP
        self.term_init = TERM_INIT
        self.term_item_types = TERM_ITEM_TYPES
        self.term_end_time = TERM_END_TIME
        self.activity_table = TABLE_ACTIVITY_PREFIX
        self.object_type_table = TABLE_OBJECT_PREFIX
        self.object_map_table = TABLE_MAPPING_OBJECT
        self.event_map_table = TABLE_MAPPING_EVENT
        self.object_qty_table = TABLE_OBJECT_QTY
        self.e2o_table = TABLE_EVENT_OBJECT
        self.o2o_table = TABLE_OBJECT_OBJECT
        self.event_table = TABLE_EVENT
        self.eqty_table = TABLE_EQTY
        self.object_table = TABLE_OBJECT

        self._event_data = event_data if event_data else dict()
        self._object_data = object_data if object_data else dict()
        self._qty_op = eqty if isinstance(eqty, pd.DataFrame) else pd.DataFrame(
            columns=[self.event_id_col, self.collection_col])
        self._e2o = e2o if isinstance(e2o, pd.DataFrame) else pd.DataFrame(
            columns=[self.e2o_event, self.e2o_object, self.qualifier])
        self._o2o = o2o if isinstance(o2o, pd.DataFrame) else pd.DataFrame(
            columns=[self.o2o_source, self.o2o_target, self.qualifier])
        self._item_levels = None
        self._event_map_type = event_map_type if isinstance(event_map_type, pd.DataFrame) \
            else pd.DataFrame(columns=[self.activity_col, self.activity_map])
        self._object_map_type = object_map_type if isinstance(object_map_type, pd.DataFrame) \
            else pd.DataFrame(columns=[self.object_type_col, self.object_map])
        self._object_quantities = object_quantities if isinstance(object_quantities, pd.DataFrame) \
            else pd.DataFrame(columns=[self.object_id_col])

        for key, value in kwargs.items():
            setattr(self, key, value)

    @property
    def item_types(self):
        return (set.union(set(self.object_quantities), set(self.active_quantity_operations.columns))
                - {self.object_id_col, self.event_id_col, self.timestamp_col, self.collection_col, self.activity_col, self.object_type_col})

    @property
    def object_type_attributes(self) -> dict:
        object_type_overview = dict()
        for ot, data in self._object_data.items():
            object_type_overview[ot] = set(data.columns) - {self.object_change, self.object_id_col,
                                                            self.object_type_col, self.timestamp_col}
        return object_type_overview

    @property
    def object_types(self) -> set:
        return set(self._object_data.keys())

    @property
    def activity_attributes(self) -> dict:
        activity_overview = dict()
        for act, data in self._event_data.items():
            activity_overview[act] = set(data.columns) - {self.event_id_col, self.activity_col, self.timestamp_col}
        return activity_overview

    @property
    def activities(self) -> set:
        return set(self._event_data.keys())

    @property
    def objects(self) -> pd.DataFrame:
        if len(self._object_data) > 0:
            obj = pd.DataFrame()
            for object_type, data in self._object_data.items():
                object_type_data = data.copy()
                object_type_data[self.object_type_col] = object_type
                obj = pd.concat([obj, object_type_data])
                obj = obj.drop_duplicates()
                obj = obj.drop(columns=[self.object_change])
            obj = obj.set_index(self.object_id_col)
            return obj
        else:
            return pd.DataFrame(columns=[self.object_id_col, self.object_type_col])

    def get_objects(self):
        if len(self._object_data) > 0:
            obj = pd.DataFrame()
            for object_type, data in self._object_data.items():
                object_type_data = data.copy()
                object_type_data[self.object_type_col] = object_type
                obj = pd.concat([obj, object_type_data])
            obj = obj.rename(columns={self.object_type_col: TERM_OBJECT_TYPE, self.object_id_col: TERM_OBJECT, self.timestamp_col: TERM_TIME, self.object_change: OBJECT_CHANGE})
        else:
            obj = pd.DataFrame(columns=[TERM_OBJECT, TERM_OBJECT_TYPE, TERM_TIME, OBJECT_CHANGE])
        return obj

    @property
    def object_names(self):
        return set(self.objects.index)

    @property
    def event_names(self):
        return set(self.events.index)

    @property
    def object_quantities(self):
        return self._object_quantities

    @property
    def events(self) -> pd.DataFrame:
        events = pd.DataFrame()
        for act, data in self._event_data.items():
            data_activity = data.copy()
            data_activity[self.activity_col] = act
            events = pd.concat([events, data_activity])
        return events

    @property
    def e2o(self) -> pd.DataFrame:
        return self._e2o

    @property
    def collection_points(self):
        return set(self._qty_op[self.collection_col].unique().copy())

    @property
    def quantity_activities(self):
        return set(self.active_quantity_operations[self.activity_col])

    @property
    def event_activity_timestamp(self):
        return self.events[[self.activity_col, self.timestamp_col]]

    def get_quantity_operations_activity(self, activity_name: str) -> pd.DataFrame:
        activity = self._identify_activity(activity_name=activity_name)
        return self.quantity_operations.loc[self.quantity_operations[self.activity_col] == activity]

    def _identify_activity(self, activity_name):
        activity_name_variations = {activity_name, activity_name.lower(), activity_name.replace("_", " "),
                                    activity_name.lower().replace("-", " "), activity_name.lower().replace("_", " "),
                                    activity_name.replace("-", " "), activity_name.replace(" ", "_").lower(),
                                    activity_name.replace(" ", "_")}
        if activity_name_variations & set(self._event_data.keys()):
            return (activity_name_variations & self._event_data.keys()).pop()
        elif activity_name_variations & set(self._event_map_type[self.activity_map].values):
            overlap = (activity_name_variations & self._event_data.keys()).pop()
            return self._event_map_type.loc[
                self._event_map_type[self.activity_map] == overlap, self.activity_col].values[0]
        else:
            raise ValueError(f"Activity {activity_name} is not part of the event log.")

    def _identify_item_type(self, item_type_name):
        item_type_name_vars = {item_type_name, item_type_name.lower(), item_type_name.replace("_", " "),
                                item_type_name.lower().replace("-", " "), item_type_name.lower().replace("_", " "),
                                item_type_name.replace("-", " "), item_type_name.replace(" ", "_").lower(),
                                item_type_name.replace(" ", "_"), "item_type_"+item_type_name.lower(),
                                "item_type_"+item_type_name, item_type_name.replace("item_type", ""),
                               item_type_name.replace("item_type_", ""), self.term_item_types+item_type_name.lower(),
                                self.term_item_types+item_type_name, item_type_name.replace(self.term_item_types, ""),
                               item_type_name.replace(self.term_item_types, "")}
        if item_type_name_vars & set(self.item_types):
            return (item_type_name_vars & self.item_types).pop()
        else:
            raise ValueError(f"Item type {item_type_name} is not part of the event log.")

    def _identify_event(self, event_name):
        event_name_vars = {event_name, event_name.lower(), event_name.replace("_", " "),
                                 event_name.lower().replace("-", " "), event_name.lower().replace("_", " "),
                                 event_name.replace("-", " "), event_name.replace(" ", "_").lower(),
                                 event_name.replace(" ", "_")}
        if event_name_vars & set(self.events.index):
            return (event_name_vars & set(self.events.index)).pop()
        elif event_name_vars & {event.replace("-", " ").replace("_", " ") for event in self.events.index}:
            overlap = (event_name_vars & {event.replace("-", " ").replace("_", " ")
                                          for event in self.events.index}).pop()
            pot_names = {overlap.replace(" ", "_"), overlap.replace(" ", "-")}
            if pot_names & set(self.events.index):
                return (pot_names & set(self.events.index)).pop()
            else:
                ValueError(f"Event {event_name} is not part of the event log.")
        else:
            raise ValueError(f"Event {event_name} is not part of the event log.")

    def get_events_of_activities(self, activities: str | list[str] | set[str]) -> set[str]:
        if isinstance(activities, str):
            activity = self._identify_activity(activity_name=activities)
            activities = [activity]
        elif isinstance(activities, set):
            activities = list(activities)
        else:
            pass

        events = self.events.reset_index()
        return set(events.loc[events[self.activity_col].isin(activities), self.event_id_col])

    @property
    def overview_quantity_relations(self):
        qr_overview = self.quantity_operations.drop(columns=[self.event_id_col, self.timestamp_col])
        return qr_overview.groupby([self.activity_col, self.collection_col]).any()

    @property
    def active_quantity_operations(self) -> pd.DataFrame:
        """Returns data frame with only quantity operations with at least one none-zero value."""

        provided_qos = self._qty_op.loc[self._qty_op[self.event_id_col] != self.term_init].copy()
        provided_qos = provided_qos.set_index([self.event_id_col, self.collection_col])
        active_qos = provided_qos.loc[(provided_qos != 0).any(axis=1)]
        active_qos = pd.merge(active_qos, self.events[[self.activity_col, self.timestamp_col]],
                              left_on=self.event_id_col, right_index=True, how="left")

        return active_qos

    @property
    def overview_active_quantity_relations(self):
        qro = self.overview_quantity_relations
        qro[self.term_active] = qro[list(self.item_types)].any(axis=1)
        return qro[self.term_active]

    @property
    def active_quantity_relations(self):
        all_qrs = self.overview_active_quantity_relations
        return set(all_qrs[all_qrs].index)


    @property
    def overview_quantity_relations_complete(self):
        """If at least one quantity update is executed every time the activity is executed."""
        qr_overview = self.active_quantity_operations.reset_index().copy()
        qr_overview = qr_overview.drop(columns=[self.event_id_col, self.timestamp_col])
        qr_overview[self.term_qop] = qr_overview[list(self.item_types)].any(axis=1)
        qactivity_overview = qr_overview[[self.term_qop, self.collection_col, self.activity_col]].groupby(
            [self.activity_col, self.collection_col]).all()
        return qactivity_overview.reset_index()

    @property
    def quantity_operations(self):
        """Every event of quantity activities now has an entry for each cp - if nothing changes it is 0"""
        # get all event ids
        event_ids = list(self.events.index)
        cps = list(self.collection_points)

        if event_ids == [] or cps == []:
            return self._qty_op
        else:
            pass

        # create a dataframe with all combinations of event ids and collection points
        combinations = list(product(event_ids, cps))
        combination_df = pd.DataFrame(combinations, columns=[self.event_id_col, self.collection_col])

        # merge with quantity operations
        extended_qop = pd.merge(combination_df, self._qty_op, on=[self.event_id_col, self.collection_col],
                                how="left").fillna(0)

        # add columns for activity and timestamp
        return pd.merge(extended_qop, self.events[[self.activity_col, self.timestamp_col]],
                        left_on=self.event_id_col, right_index=True, how="left")

    @property
    def overview_item_types_collections(self):
        """Returns a dataframe with all item types and collection points and a boolean value if the item type is"""

        qop = self.quantity_operations
        qop = convert_numeric_columns(qop)

        for cp in self.collection_points:
            qop.loc[f"{self.term_init}-{cp}"] = dict(self.get_initial_item_level_cp(cp=cp))
            qop.loc[f"{self.term_init}-{cp}", self.collection_col] = cp

        qop = qop.drop(columns=[self.event_id_col, self.timestamp_col, self.activity_col])
        qop = qop.groupby(self.collection_col).any()

        return qop

    @property
    def item_types_collection(self):
        overview = self.overview_item_types_collections
        overview = overview.replace(False, np.nan)

        item_types_collections = dict()
        for cp in self.collection_points:
            item_types_collections[cp] = set(overview.loc[cp].dropna().index)

        return item_types_collections

    def get_quantity_update(self, event_name: str, cp: str) -> Counter:
        event = self._identify_event(event_name=event_name)
        qty = self.quantity_operations.set_index([self.event_id_col, self.collection_col])
        if (event, cp) in qty.index:
            return Counter(qty.select_dtypes(include='number').loc[(event, cp)].to_dict())
        else:
            return Counter()

    def get_quantity_operations_cp(self, cp: str, active: bool = False) -> pd.DataFrame:

        if active:
            qop = self.active_quantity_operations.reset_index()
            qop_cp = qop.loc[qop[self.collection_col] == cp].copy()
        else:
            qop_cp = self.quantity_operations.loc[self.quantity_operations[self.collection_col] == cp]

        qop_cp[self.timestamp_col] = pd.to_datetime(qop_cp[self.timestamp_col])
        qop_sorted = qop_cp.sort_values(by=self.timestamp_col, ascending=True)

        return qop_sorted

    def get_associated_activities_for_collection(self, cp: str) -> set:
        return set(self.get_quantity_operations_cp(cp=cp, active=True)[self.activity_col].unique())

    # def get_collection_point(self, cp_name: str) -> CollectionPointLog:
    #     cp_name = self._identify_cp(cp_name=cp_name)
    #     return {cp for cp in self.collection_points if cp.name == cp_name}.pop()

    def get_initial_item_level_cp(self, cp: str) -> Counter:
        return Counter(self._qty_op.loc[(self._qty_op[self.event_id_col] == self.term_init) &
                                        (self._qty_op[self.collection_col] == cp),
                                        list(set(self._qty_op.columns) - {self.event_id_col, self.collection_col})].to_dict(orient="records")[0])

    def set_file_path(self, path_to_file):
        self.file_path = path_to_file

    def get_activity(self, event_id):
        """
        Searches for event_id in series of all events and activities
        :param event_id: Event identifier that can be found in event_id_col
        :return: activity name that can be found in activity_col
        """
        return self.events.loc[event_id, self.activity_col]

    def get_object_type(self, object_id):
        return self.objects.loc[object_id, self.object_type_col]

    def get_event_data_activity(self, activity_name):
        return self._event_data[activity_name]

    def get_earliest_timestamp_log(self):
        self.events[self.timestamp_col] = pd.to_datetime(self.events[self.timestamp_col])
        return self.events[self.timestamp_col].min()

    def get_latest_timestamp_log(self):
        return self.events[self.timestamp_col].max()

    @property
    def o2o(self):
        return self._o2o

    def _add_event_to_event_data(self, event: Event):
        """Adds passed event object to dataframe documenting events of that activity."""

        if event.log_event:
            pass
        else:
            return

        activity_name = event.activity.activity_name

        if event.end_timestamp:
            # get non-standard attributes as dict
            event_entry = {attribute: value for attribute, value in vars(event).items() if
                           attribute not in Event.default_attributes | {"_end_timestamp"} | {self.term_end_time}}
            event_entry[self.term_end_time] = event.end_timestamp
        else:
            pass

        # add other attributes
        event_entry = {attribute: value for attribute, value in vars(event).items() if
                           attribute not in (Event.default_attributes | {"_end_timestamp"} | {self.term_end_time})}

        # add timestamp
        event_entry[self.timestamp_col] = event.timestamp

        # create series and set index
        event_series = pd.Series(event_entry, name=event.name)

        # add to existing dataframe or create new one
        if activity_name in self._event_data.keys():
            self._event_data[activity_name] = pd.concat(
                [self._event_data[activity_name], event_series.to_frame().transpose()])
        else:
            self._event_data[activity_name] = event_series.to_frame().transpose()
            self._event_map_type = pd.concat([self._event_map_type,
                                              pd.Series({self.activity_col: event.activity.activity_name,
                                                         self.activity_map: event.activity.__name__}).to_frame().transpose()])

        self._event_data[activity_name].index = self._event_data[activity_name].index.rename(self.event_id_col)

    def _add_event_to_object_relationship(self, event: Event):
        """Adds event to object relationship to log."""

        if event.log_event:
            pass
        else:
            return

        if event.name in self.event_names:
            pass
        else:
            self.add_event_to_log(event=event)

        for obj in event.objects:

            if obj.log_object:
                pass
            else:
                continue

            if obj.name in self.object_names:
                pass
            else:
                self.add_object_entry(obj=obj)

            # create dict with required data
            new_entry = dict()
            new_entry[self.e2o_event] = event.name
            new_entry[self.e2o_object] = obj.name

            if obj in event.qualified_relationship.keys():
                new_entry[self.qualifier] = event.qualified_relationship[obj]
            else:
                pass

            # add row to e2o dataframe
            # new_row = pd.Series(new_entry)
            self._e2o.loc[len(self._e2o)] = new_entry

    def add_event_to_log(self, event: Event):
        """Pass event object to add entry in event log."""

        if event.log_event:
            pass
        else:
            return

        # add event to event data
        self._add_event_to_event_data(event=event)

        # add e2o relationship
        self._add_event_to_object_relationship(event=event)

        # add quantity operations
        for collection_point, quantity_update in event.quantity_operations.items():
            if collection_point.silent:
                pass
            else:
                self.add_quantity_operation(event=event, collection_point=collection_point, quantity_operation=quantity_update)

    def add_object_entry(self, obj: Object):
        """Pass object and add entry to object_data."""

        if obj.log_object:
            pass
        else:
            return

        object_type = obj.object_type.object_type_name

        # get non-standard attributes as dict
        obj_entry = {attribute: value for attribute, value in vars(obj).items() if
                     attribute not in Object.default_attributes}

        # add timestamp
        obj_entry[self.timestamp_col] = obj.last_change_attributes
        obj_entry[self.object_id_col] = obj.name

        # add to existing dataframe or create new one
        if object_type in self._object_data.keys():
            pass
        else:
            self._object_data[object_type] = pd.DataFrame(columns=[self.object_id_col,
                                                                   self.timestamp_col,
                                                                   self.object_change])
            self._object_map_type = pd.concat([self._object_map_type,
                                               pd.Series({self.object_type_col: object_type,
                                                          self.object_map: obj.object_type.__name__}).to_frame().T])

        for changed_attr in obj.changed_attributes:
            change_entry = obj_entry.copy()
            change_entry[self.object_change] = changed_attr
            change_series = pd.Series(change_entry)
            self._object_data[object_type] = pd.concat([self._object_data[object_type], change_series.to_frame().T],
                                                       ignore_index=True)

        if len(obj.changed_attributes) == 0:
            obj_entry_series = pd.Series(obj_entry)
            self._object_data[object_type] = pd.concat([self._object_data[object_type], obj_entry_series.to_frame().T],
                                                       ignore_index=True)

        obj.clear_changed_attributes()
        self.add_object_quantities(obj=obj)

    def get_o2o_relationship_of_object(self, obj: Object | str):
        """Pass object get all o2o relationships from this object to other objects."""

        if obj.log_object:
            pass
        else:
            return

        obj_name = self._sup_get_object_name(obj=obj)

        return self._o2o.loc[self._o2o[self.o2o_source] == obj_name]

    def add_object_quantities(self, obj: Object):
        """Pass object and add object quantities to log."""

        if obj.log_object:
            pass
        else:
            return

        if obj.name in self._object_quantities.index:
            return
        else:
            quantities = dict(obj.quantities.copy())
            quantities[self.object_id_col] = obj.name
            quantities_series = pd.Series(quantities)
            self._object_quantities = pd.concat([self._object_quantities, quantities_series.to_frame().T],
                                                ignore_index=True)

    def add_o2o_relationship(self, source_object: Object):
        """Pass object add all new o2o relationships."""

        for target_object, qualifier in source_object.o2o.items():

            if target_object.name in self.object_names:
                pass
            else:
                self.add_object_entry(obj=target_object)

            if qualifier == "":
                qualifier = np.nan

            new_entry = pd.Series({self.o2o_source: source_object.name,
                                   self.o2o_target: target_object.name,
                                   self.qualifier: qualifier})

            self._o2o = pd.concat([self._o2o, new_entry.to_frame().T], ignore_index=True)

        self._o2o = self._o2o.drop_duplicates()

    def add_object_to_log(self, obj: Object):
        """Pass object object and add to event log (object data and o2o relationship)."""

        if obj.log_object:
            pass
        else:
            return

        # add object data
        self.add_object_entry(obj=obj)

        # add o2o relationships of object
        self.add_o2o_relationship(source_object=obj)

    def add_quantity_operation(self, collection_point: CollectionPoint, quantity_operation: Counter, event: Event = None):
        """Pass quantity operation and add to log."""

        # create data for entry
        new_entry = dict(quantity_operation)
        new_entry[self.event_id_col] = event.name if isinstance(event, Event) else TERM_INIT
        new_entry[self.collection_col] = collection_point.label

        # add to log
        new_entry_series = pd.Series(new_entry)
        self._qty_op = pd.concat([self._qty_op, new_entry_series.to_frame().T], ignore_index=True)

    def get_event_objects(self, event: Event | str) -> list:
        """Pass event object or event name and get names of all involved objects."""

        event_name = self._sup_get_event_name(event=event)

        involved_objects = self.e2o.loc[self.e2o[self.e2o_event] == event_name, self.e2o_object]

        return involved_objects

    def get_object_info(self, obj: Object | str) -> pd.DataFrame:
        """Pass object or object name and get information on object and anttributes."""

        object_name = self._sup_get_object_name(obj=obj)

        return self.objects.loc[object_name, self.object_type_col].drop_duplicates().reset_index()

    def get_event_object_info(self, event: Event | str) -> pd.DataFrame:
        """Pass event or event name and get all object info on involved objects"""

        # get objects
        involved_objects = self.get_event_objects(event=event)

        # get object data
        event_object_info = pd.DataFrame()
        for obj in involved_objects:

            if isinstance(obj, Object):
                if obj.log_object:
                    pass
                else:
                    continue
            else:
                pass

            object_info = self.get_object_info(obj=obj)
            event_object_info = pd.concat([event_object_info, object_info], ignore_index=True)

        return event_object_info

    def _sup_get_event_name(self, event: Event | str):

        if isinstance(event, Event):
            return event.name
        else:
            return event

    def _sup_get_object_name(self, obj: Object | str):

        if isinstance(obj, Object):
            return obj.name
        else:
            return obj

    def create_event_tables(self):
        """Create event tables for export."""

        tables = dict()
        tables[self.event_table] = self.events[self.activity_col].copy()
        tables[self.event_map_table] = self._event_map_type.copy().set_index(self.activity_col)
        tables[self.e2o_table] = self._e2o.copy().set_index([self.e2o_event, self.e2o_object])

        for activity_name, data in self._event_data.items():
            activity_table_name = tables[self.event_map_table].loc[activity_name, self.activity_map]
            table_name = f"{self.activity_table}{activity_table_name}"
            tables[table_name] = data

        return tables

    def create_object_tables(self):
        """Create object tables for export."""

        tables = dict()

        tables[self.object_table] = self.objects[self.object_type_col].copy()
        tables[self.object_map_table] = self._object_map_type.copy().set_index(self.object_type_col)
        tables[self.o2o_table] = self._o2o.copy().set_index([self.o2o_source, self.o2o_target, self.qualifier])

        for object_type, data in self._object_data.items():
            object_type_table_name = tables[self.object_map_table].loc[object_type, self.object_map]
            file_name = f"{self.object_type_table}{object_type_table_name}"
            tables[file_name] = data

        return tables

    def create_quantity_tables(self):
        """Create quantity tables for export."""

        tables = dict()

        tables[self.eqty_table] = self._qty_op.copy().set_index([self.event_id_col, self.collection_col])
        tables[self.object_qty_table] = self._object_quantities.copy().set_index(self.object_id_col)

        return tables

    def save_event_logs_to_sql_lite(self, path_to_folder=None):
        if path_to_folder:
            if path_to_folder[-1] == "/":
                pass
            else:
                path_to_folder = f"{path_to_folder}/"
        else:
            path_to_folder = "/event_log/"

        if not os.path.exists(path_to_folder[:-1]):
            os.mkdir(path_to_folder[:-1])
        else:
            pass
        time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
        sql_path = f"{path_to_folder}{time}_{self.name}.sqlite"
        if os.path.exists(sql_path):
            os.remove(sql_path)

        engine = create_engine(f"sqlite:///{sql_path}")

        for list_of_tables in [self.create_event_tables(), self.create_object_tables(),
                               self.create_quantity_tables()]:
            for name, log in list_of_tables.items():
                log.to_sql(name, con=engine, index=True, if_exists="replace")

        engine.dispose()

        return

    def get_events_in_interval(self, start: datetime.datetime, end: datetime.datetime):
        events = self.events.copy()
        events[self.timestamp_col] = pd.to_datetime(events[self.timestamp_col])
        return events[(events[self.timestamp_col] >= start) & (events[self.timestamp_col] <= end)]

    def get_quantity_events(self):
        qop = self.active_quantity_operations
        qop = qop.reset_index()
        return set(qop[self.event_id_col])

    def get_objects_of_object_type(self, object_type: str) -> set[str]:
        return set(self.objects.loc[self.objects[self.object_type_col] == object_type].index)

    def get_events_with_object_type(self, object_type: str) -> set[str]:
        objects = self.get_objects_of_object_type(object_type=object_type)
        return set(self.e2o.loc[self.e2o[self.e2o_object].isin(objects), self.e2o_event])

    def get_events_with_qop_to_cp(self, cp: str) -> set[str]:
        if cp in self.collection_points:
            pass
        else:
            raise ValueError(f"Collection {cp} is not part of the event log.")
        qop = self.active_quantity_operations
        qop = qop.reset_index()
        return set(qop.loc[qop[self.collection_col] == cp, self.event_id_col])


    def get_qops_for_cp(self, cp: str) -> pd.DataFrame:
        if cp in self.collection_points:
            pass
        else:
            raise ValueError(f"Collection {cp} is not part of the event log.")
        qop = self.active_quantity_operations
        qop = qop.reset_index()
        qop = qop.rename(columns={self.event_id_col: TERM_EVENT, self.collection_col: TERM_COLLECTION})
        return qop.loc[qop[TERM_COLLECTION] == cp, [TERM_EVENT, TERM_COLLECTION]].to_dict("records")

    def get_qactivities_for_cp(self, cp: str) -> set[str]:
        if cp in self.collection_points:
            pass
        else:
            raise ValueError(f"Collection {cp} is not part of the event log.")
        qop = self.active_quantity_operations
        qop = qop.reset_index()
        return set(qop.loc[qop[self.collection_col] == cp, self.activity_col].unique())


    def get_quantity_relations(self):
        active_qops = self.active_quantity_operations
        active_qops = active_qops.reset_index()
        active_qops = active_qops.rename(columns={self.activity_col: TERM_ACTIVITY, self.collection_col: TERM_COLLECTION})
        active_qops = active_qops[[TERM_ACTIVITY, TERM_COLLECTION]].groupby([TERM_ACTIVITY, TERM_COLLECTION]).size().reset_index()
        return active_qops[[TERM_ACTIVITY, TERM_COLLECTION]].to_dict("records")

    def get_item_level_development(self, cp: str, post_event: bool = True):

        ilvl = self.quantity_operations.loc[self.quantity_operations[self.collection_col] == cp, :]
        # format timestamps and get earliest timestamp
        ilvl[self.timestamp_col] = pd.to_datetime(ilvl[self.timestamp_col])
        earliest_timestamp = ilvl[self.timestamp_col].min()

        # add initial item level
        ilvl.loc[len(ilvl) + 1] = dict(self.get_initial_item_level_cp(cp=cp))
        ilvl.loc[len(ilvl) + 1, self.event_id_col] = TERM_INIT
        ilvl.loc[len(ilvl) + 1, self.activity_col] = TERM_INIT
        ilvl.loc[len(ilvl) + 1, self.timestamp_col] = earliest_timestamp - datetime.timedelta(seconds=1)

        # sort by timestamp
        ilvl = ilvl.sort_values(by=self.timestamp_col, ascending=True)

        # set all non-item type columns as index to simplify the rest
        ilvl = ilvl.set_index([self.event_id_col, self.activity_col, self.timestamp_col, self.collection_col])

        # apply accumulated sum so that item levels are determined
        ilvl = ilvl.cumsum()

        if post_event:
            pass
        else:
            ilvl = ilvl.shift(1)
            ilvl = ilvl.fillna(0)
            ilvl = ilvl.drop(index=[TERM_INIT, TERM_INIT, earliest_timestamp - datetime.timedelta(seconds=1)])

        ilvl = ilvl.reset_index()

        ilvl = ilvl.rename(columns={self.event_id_col: TERM_EVENT,
                                    self.activity_col: TERM_ACTIVITY,
                                    self.timestamp_col: TERM_TIME,
                                    self.collection_col: TERM_COLLECTION})

        return ilvl

    def get_quantity_operations(self):
        qop = self.quantity_operations
        qop = qop.rename(columns={self.event_id_col: TERM_EVENT, self.collection_col: TERM_COLLECTION,
                                  self.activity_col: TERM_ACTIVITY, self.timestamp_col: TERM_TIME})
        return qop

    def get_object_types_for_cp(self, cp: str):
        if cp in self.collection_points:
            pass
        else:
            raise ValueError(f"Collection {cp} is not part of the event log.")
        events = self.get_events_with_qop_to_cp(cp=cp)
        objects = self.get_objects_of_events(events=events)
        return self.get_object_types_of_objects(objects=objects)

    def get_objects_of_events(self, events: set[str]):
        return set(self.e2o.loc[self.e2o[self.e2o_event].isin(list(events)), self.e2o_object])

    def get_events_of_objects(self, objects: set[str]):
        return set(self.e2o.loc[self.e2o[self.e2o_object].isin(list(objects)), self.e2o_event])

    def get_object_types_of_objects(self, objects: set):
        return set(self.objects.loc[list(objects), self.object_type_col])

    def get_events_of_activity_with_active_qop(self, activity: str):
        if activity in self.activities:
            pass
        else:
            raise ValueError(f"Activity {activity} is not part of the event log.")
        qop = self.active_quantity_operations
        qop = qop.reset_index()
        return set(qop.loc[qop[self.activity_col] == activity, self.event_id_col])

    def get_qops_for_activity(self, activity: str) -> pd.DataFrame:
        if activity in self.activities:
            pass
        else:
            raise ValueError(f"Activity {activity} is not part of the event log.")
        qop = self.active_quantity_operations
        qop = qop.reset_index()
        events = self.get_events_of_activity_with_active_qop(activity=activity)
        qop = qop.rename(columns={self.event_id_col: TERM_EVENT, self.collection_col: TERM_COLLECTION})
        return qop.loc[qop[TERM_EVENT].isin(list(events)), [TERM_EVENT, TERM_COLLECTION]].to_dict("records")

    def get_objects_for_activity(self, activity: str) -> set[str]:
        if activity in self.activities:
            pass
        else:
            raise ValueError(f"Activity {activity} is not part of the event log.")
        events = self.get_events_of_activities(activity)
        return self.get_objects_of_events(events=events)

    def get_objects_for_cp(self, cp: str):
        if cp in self.collection_points:
            pass
        else:
            raise ValueError(f"Collection {cp} is not part of the event log.")
        events = self.get_events_with_qop_to_cp(cp=cp)
        return self.get_objects_of_events(events=events)

    def get_activities_of_events(self, events: set[str]) -> set[str]:
        return set(self.events.loc[list(events), self.activity_col])

    def get_object_types_for_activity(self, activity: str):
        if activity in self.activities:
            pass
        else:
            raise ValueError(f"Activity {activity} is not part of the event log.")
        objects = self.get_objects_for_activity(activity=activity)
        return self.get_object_types_of_objects(objects=objects)

    def get_collections_with_activity(self, activity: str):
        if activity in self.activities:
            pass
        else:
            raise ValueError(f"Activity {activity} is not part of the event log.")
        qop = self.active_quantity_operations
        qop = qop.reset_index()
        return set(qop.loc[qop[self.activity_col] == activity, self.collection_col])

    def get_qevents_of_object_type(self, object_type: str) -> set[str]:
        events = self.get_events_with_object_type(object_type=object_type)
        qop = self.active_quantity_operations
        qop = qop.reset_index()
        return set(qop.loc[qop[self.event_id_col].isin(list(events)), self.event_id_col])

    def get_qops_with_object_type(self, object_type: str):
        qop = self.active_quantity_operations
        qop = qop.reset_index()
        events = self.get_events_with_object_type(object_type=object_type)
        qop = qop.rename(columns={self.event_id_col: TERM_EVENT, self.collection_col: TERM_COLLECTION})
        return qop.loc[qop[TERM_EVENT].isin(list(events)), [TERM_EVENT, TERM_COLLECTION]].to_dict("records")

    def get_qactivities_for_object_type(self, object_type):
        qop = self.active_quantity_operations
        qop = qop.reset_index()
        events = self.get_events_with_object_type(object_type=object_type)
        return set(qop.loc[qop[self.event_id_col].isin(list(events)), self.activity_col])

    def get_item_types_for_activity(self, activity: str):
        if activity in self.activities:
            pass
        else:
            raise ValueError(f"Activity {activity} is not part of the event log.")
        qop = self.active_quantity_operations
        qop = qop.reset_index()
        qop = qop.loc[qop[self.activity_col] == activity, :]
        qop = qop.loc[:, (qop != 0).any()]
        non_item_type_columns = {self.event_id_col, self.timestamp_col, self.collection_col, self.activity_col}
        return set(qop.columns) - non_item_type_columns

    def get_collections_with_object_type(self, object_type: str):
        if object_type in self.object_types:
            pass
        else:
            raise ValueError(f"Object type {object_type} is not part of the event log.")
        events = self.get_events_with_object_type(object_type=object_type)
        qop = self.active_quantity_operations
        qop = qop.reset_index()
        return set(qop.loc[qop[self.event_id_col].isin(list(events)), self.collection_col])

    def get_item_types_with_object_type(self, object_type: str):
        if object_type in self.object_types:
            pass
        else:
            raise ValueError(f"Object type {object_type} is not part of the event log.")
        events = self.get_events_with_object_type(object_type=object_type)
        qop = self.active_quantity_operations
        qop = qop.reset_index()
        qop = qop.loc[qop[self.event_id_col].isin(list(events)), :]
        qop = qop.loc[:, (qop != 0).any()]
        non_item_type_columns = {self.event_id_col, self.timestamp_col, self.collection_col, self.activity_col}
        return set(qop.columns) - non_item_type_columns

    def get_e2o_relationships(self):
        e2o = self.e2o.loc[:, [self.e2o_event, self.e2o_object]]
        e2o = e2o.rename(columns={self.e2o_event: TERM_EVENT, self.e2o_object: TERM_OBJECT})
        objects = self.objects[self.object_type_col].reset_index().drop_duplicates()
        objects = objects.rename(columns={self.object_type_col: TERM_OBJECT_TYPE, self.object_id_col: TERM_OBJECT})
        e2o = e2o.merge(objects, on=TERM_OBJECT, how='left')
        return e2o

    def get_events(self):
        events = self.events
        events = events.reset_index()
        events = events.rename(columns={self.activity_col: TERM_ACTIVITY,
                                  self.timestamp_col: TERM_TIME, self.event_id_col: TERM_EVENT})

        return events

    def get_qty_objects(self):
        qevents = self.get_quantity_events()
        return self.get_objects_of_events(events=qevents)

    def get_object_types_for_objects(self, objects: set[str]):
        if objects.issubset(self.object_names):
            pass
        else:
            raise ValueError("Not all objects are part of the event log.")
        return set(self.objects.loc[list(objects), self.object_type_col])

    def get_qty_object_types(self):
        qty_objects = self.get_qty_objects()
        return self.get_object_types_for_objects(objects=qty_objects)

    def get_qty_subset_of_objects(self, objects: set[str]) -> set[str]:
        """Pass a set of objects and get all objects involved in at least one event with an active quantity operation."""
        if objects.issubset(self.object_names):
            pass
        else:
            raise ValueError("Not all objects are part of the event log.")
        # get objects of qty events
        qty_objects = self.get_qty_objects()

        return qty_objects.intersection(objects)

    def get_qty_subset_of_object_types(self, object_types: set[str]) -> set[str]:
        if object_types.issubset(self.object_types):
            pass
        else:
            raise ValueError("Not all object types are part of the event log.")

        qty_ots = self.get_qty_object_types()
        return qty_ots.intersection(object_types)

    def get_qty_subset_of_activities(self, activities: set[str]) -> set[str]:
        """Pass a set of activities and get all activities with at least one active quantity operation."""
        if activities.issubset(self.activities):
            pass
        else:
            raise ValueError("Not all activities are part of the event log.")

        qactivities = self.quantity_activities

        return qactivities.intersection(activities)

    def get_activities_with_object_type(self, object_type: str):
        if object_type in self.object_types:
            pass
        else:
            raise ValueError(f"Object type {object_type} is not part of the event log.")
        events = self.get_events_with_object_type(object_type=object_type)
        return self.get_activities_of_events(events=events)

