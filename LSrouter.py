####################################################
# LSrouter.py
# Name:
# HUID:
####################################################

import json
import heapq
from router import Router
from packet import Packet


class LSrouter(Router):
    def __init__(self, router_addr, heartbeat_interval):
        super().__init__(router_addr)

        self.heartbeat_interval = heartbeat_interval
        self.last_broadcast_time = 0

        # {port: (neighbor_addr, link_cost)}
        self.neighbor_ports = {}

        # {
        #   router_addr: {
        #       "sequence_number": int,
        #       "links": {neighbor_addr: cost}
        #   }
        # }
        self.link_state_database = {
            self.addr: {
                "sequence_number": 0,
                "links": {}
            }
        }

        # {destination_addr: output_port}
        self.forwarding_table = {}

        # Sequence number cho LSA của chính router này
        self.sequence_number = 0

    def _get_current_links(self):
        return {
            neighbor_addr: cost
            for neighbor_addr, cost in self.neighbor_ports.values()
        }

    def _create_lsa_packet(self, destination_addr):
 
        lsa_content = json.dumps({
            "origin_router": self.addr,
            "sequence_number": self.sequence_number,
            "links": self._get_current_links()
        })

        return Packet(
            kind=Packet.ROUTING,
            src_addr=self.addr,
            dst_addr=destination_addr,
            content=lsa_content
        )

    def _broadcast_lsa(self, excluded_port=None):
        """
        Flood LSA của chính mình tới tất cả neighbors.
        """
        for port, (neighbor_addr, _) in self.neighbor_ports.items():

            if port == excluded_port:
                continue

            lsa_packet = self._create_lsa_packet(neighbor_addr)
            self.send(port, lsa_packet)

    def _forward_received_lsa(self, lsa_content, incoming_port):
        for port, (neighbor_addr, _) in self.neighbor_ports.items():

            if port == incoming_port:
                continue

            forwarded_packet = Packet(
                kind=Packet.ROUTING,
                src_addr=self.addr,
                dst_addr=neighbor_addr,
                content=lsa_content
            )

            self.send(port, forwarded_packet)

    def _run_dijkstra(self):

        shortest_distance = {
            self.addr: 0
        }

        previous_node = {}

        priority_queue = [(0, self.addr)]

        visited_nodes = set()

        while priority_queue:

            current_distance, current_node = heapq.heappop(priority_queue)

            if current_node in visited_nodes:
                continue

            visited_nodes.add(current_node)

            if current_node not in self.link_state_database:
                continue

            neighbor_links = self.link_state_database[current_node]["links"]

            for neighbor_node, link_cost in neighbor_links.items():

                if neighbor_node in visited_nodes:
                    continue

                new_distance = current_distance + link_cost

                old_distance = shortest_distance.get(
                    neighbor_node,
                    float("inf")
                )

                if new_distance < old_distance:

                    shortest_distance[neighbor_node] = new_distance

                    previous_node[neighbor_node] = current_node

                    heapq.heappush(
                        priority_queue,
                        (new_distance, neighbor_node)
                    )

        return shortest_distance, previous_node

    def _update_forwarding_table(self):

        _, previous_node = self._run_dijkstra()

        neighbor_to_port = {
            neighbor_addr: port
            for port, (neighbor_addr, _)
            in self.neighbor_ports.items()
        }

        new_forwarding_table = {}

        for destination_addr in previous_node:

            if destination_addr == self.addr:
                continue

            current_node = destination_addr

            while previous_node.get(current_node) != self.addr:

                current_node = previous_node[current_node]

            if current_node in neighbor_to_port:

                output_port = neighbor_to_port[current_node]

                new_forwarding_table[destination_addr] = output_port

        self.forwarding_table = new_forwarding_table


    def handle_packet(self, incoming_port, packet):

        if packet.is_traceroute:

            destination_addr = packet.dst_addr

            if destination_addr in self.forwarding_table:

                output_port = self.forwarding_table[destination_addr]

                self.send(output_port, packet)

        else:

            lsa_data = json.loads(packet.content)

            origin_router = lsa_data["origin_router"]

            received_sequence_number = lsa_data["sequence_number"]

            received_links = lsa_data["links"]

            stored_lsa = self.link_state_database.get(origin_router)

            if (
                stored_lsa is not None
                and stored_lsa["sequence_number"]
                >= received_sequence_number
            ):
                return

            self.link_state_database[origin_router] = {
                "sequence_number": received_sequence_number,
                "links": received_links
            }

            self._update_forwarding_table()

            self._forward_received_lsa(
                packet.content,
                incoming_port
            )

    def handle_new_link(self, port, neighbor_addr, link_cost):

        self.neighbor_ports[port] = (
            neighbor_addr,
            link_cost
        )

        # Update LSA của chính mình
        self.sequence_number += 1

        self.link_state_database[self.addr] = {
            "sequence_number": self.sequence_number,
            "links": self._get_current_links()
        }

        self._update_forwarding_table()

        self._broadcast_lsa()

    def handle_remove_link(self, port):

        if port not in self.neighbor_ports:
            return

        self.neighbor_ports.pop(port)

        # Update LSA của chính mình
        self.sequence_number += 1

        self.link_state_database[self.addr] = {
            "sequence_number": self.sequence_number,
            "links": self._get_current_links()
        }

        self._update_forwarding_table()

        self._broadcast_lsa()

    def handle_time(self, current_time_ms):

        if (
            current_time_ms - self.last_broadcast_time
            >= self.heartbeat_interval
        ):

            self.last_broadcast_time = current_time_ms

            self.sequence_number += 1

            self.link_state_database[self.addr] = {
                "sequence_number": self.sequence_number,
                "links": self._get_current_links()
            }

            self._broadcast_lsa()

    def __repr__(self):

        return (
            f"LSrouter("
            f"addr={self.addr}, "
            f"seq={self.sequence_number}, "
            f"fwd={self.forwarding_table}"
            f")"
        )