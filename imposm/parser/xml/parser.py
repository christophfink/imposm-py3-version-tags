# Copyright 2011 Omniscale GmbH & Co. KG
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import with_statement

from marshal import dumps

from imposm.parser.util import OSMMetadata
from imposm.parser.xml.util import log_file_on_exception, iterparse


class XMLParser(object):
    def __init__(self, nodes_callback=None, ways_callback=None,
        relations_callback=None, coords_callback=None, nodes_tag_filter=None,
        ways_tag_filter=None, relations_tag_filter=None,
        marshal_elem_data=False, with_metadata=False):
        self.nodes_callback = nodes_callback
        self.ways_callback = ways_callback
        self.relations_callback = relations_callback
        self.coords_callback = coords_callback
        self.nodes_tag_filter = nodes_tag_filter
        self.ways_tag_filter = ways_tag_filter
        self.relations_tag_filter = relations_tag_filter
        self.marshal_elem_data = marshal_elem_data
        self.with_metadata = with_metadata

    def _get_int_or_none(self, obj, key):
        if key in obj:
            return int(obj[key])
        else:
            return None

    def get_metadata(self, elem):
        meta = OSMMetadata(
            version=self._get_int_or_none(elem.attrib, 'version'),
            changeset=self._get_int_or_none(elem.attrib, 'changeset'),
            timestamp=elem.attrib.get('timestamp'),
            user_id=self._get_int_or_none(elem.attrib, 'uid'),
            user_name=elem.attrib.get('user')
        )
        return meta

    def parse(self, xml):
        with log_file_on_exception(xml):
            coords = []
            nodes = []
            ways = []
            relations = []
            tags = {}
            refs = []
            members = []
            root, context = iterparse(xml)

            for event, elem in context:
                if event == 'start': continue
                if elem.tag == 'tag':
                    tags[elem.attrib['k']] = elem.attrib['v']
                elif elem.tag == 'node':
                    osmid = int(elem.attrib['id'])
                    x, y = float(elem.attrib['lon']), float(elem.attrib['lat'])
                    if self.coords_callback:
                        coords.append((osmid, x, y))
                    if self.nodes_tag_filter:
                        self.nodes_tag_filter(tags)
                    if tags and self.nodes_callback:
                        if self.marshal_elem_data:
                            node = (osmid, dumps((tags, (x, y)), 2))
                        else:
                            node = (osmid, tags, (x, y))
                        if self.with_metadata:
                            node = node + (self.get_metadata(elem),)
                        nodes.append(node)
                    tags = {}
                elif elem.tag == 'nd':
                    refs.append(int(elem.attrib['ref']))
                elif elem.tag == 'member':
                    members.append((int(elem.attrib['ref']), elem.attrib['type'], elem.attrib['role']))
                elif elem.tag == 'way':
                    osm_id = int(elem.attrib['id'])
                    if self.ways_tag_filter:
                        self.ways_tag_filter(tags)
                    if self.ways_callback:
                        if self.marshal_elem_data:
                            way = (osm_id, dumps((tags, refs), 2))
                        else:
                            way = (osm_id, tags, refs)
                        if self.with_metadata:
                            way = way + (self.get_metadata(elem),)
                        ways.append(way)
                    refs = []
                    tags = {}
                elif elem.tag == 'relation':
                    osm_id = int(elem.attrib['id'])
                    if self.relations_tag_filter:
                        self.relations_tag_filter(tags)
                    if tags and self.relations_callback:
                        if self.marshal_elem_data:
                            relation = (osm_id, dumps((tags, members), 2))
                        else:
                            relation = (osm_id, tags, members)
                        if self.with_metadata:
                            relation = relation + (self.get_metadata(elem),)
                        relations.append(relation)
                    members = []
                    tags = {}

                if len(coords) >= 512:
                    self.coords_callback(coords)
                    coords = []
                if len(nodes) >= 128:
                    self.nodes_callback(nodes)
                    nodes = []
                if len(relations) >= 128:
                    self.relations_callback(relations)
                    relations = []
                if len(ways) >= 128:
                    self.ways_callback(ways)
                    ways = []

                root.clear()

            if self.coords_callback:
                self.coords_callback(coords)
            if self.nodes_callback:
                self.nodes_callback(nodes)
            if self.ways_callback:
                self.ways_callback(ways)
            if self.relations_callback:
                self.relations_callback(relations)