####################################################
# DVrouter.py
# Name:
# HUID:
#####################################################

from router import Router
from packet import Packet
import json

class DVrouter(Router):
    """Distance vector routing protocol implementation.

    Add your own class fields and initialization code (e.g. to create forwarding table
    data structures). See the `Router` base class for docstrings of the methods to
    override.
    """
    INFINITY = 16

    def __init__(self, addr, heartbeat_time):
        Router.__init__(self, addr)  # Initialize base class - DO NOT REMOVE

        self.heartbeat_time = heartbeat_time
        self.last_broadcast_time = 0

        # {destination_address: total_cost}
        self.distance_vector = {self.addr: 0}

        # {destination_address: output_port}
        self.forwarding_table = {}

        # {port: (neighbor_address, link_cost)}
        self.neighbor_links = {}

        # {neighbor_address: {destination: cost}}
        self.received_distance_vectors = {}


    def _recompute_routes(self):
        updated_distance_vector = {self.addr: 0}
        updated_forwarding_table = {}

        # Chứa tất cả các hàng xóm và đích đến mà chúng ta đã nhận được từ các hàng xóm
        all_destinations = set()

        for neighbor_distance_vector in self.received_distance_vectors.values():
            all_destinations.update(neighbor_distance_vector.keys())

        # Tính toán chi phí tốt nhất đến mỗi đích đến thông qua mỗi hàng xóm
        for destination in all_destinations:

            if destination == self.addr:
                continue

            best_cost = INFINITY
            best_output_port = None

            for port, (neighbor_address, link_cost) in self.neighbor_links.items():

                if neighbor_address not in self.received_distance_vectors:
                    continue

                neighbor_distance_vector = (
                    self.received_distance_vectors[neighbor_address]
                )

                neighbor_cost_to_destination = (
                    neighbor_distance_vector.get(destination, INFINITY)
                )

                total_cost = link_cost + neighbor_cost_to_destination

                if total_cost < best_cost:
                    best_cost = total_cost
                    best_output_port = port 

            if best_cost < INFINITY:
                updated_distance_vector[destination] = best_cost
                updated_forwarding_table[destination] = best_output_port

        #Xử lý các hàng xóm trực tiếp (nếu chi phí đến hàng xóm đó tốt hơn chi phí đã biết đến đích đến của hàng xóm đó)
        for port, (neighbor_address, link_cost) in self.neighbor_links.items():

            if (
                neighbor_address not in updated_distance_vector
                or link_cost < updated_distance_vector[neighbor_address]
            ):
                updated_distance_vector[neighbor_address] = link_cost
                updated_forwarding_table[neighbor_address] = port

        routing_changed = (
            updated_distance_vector != self.distance_vector
            or updated_forwarding_table != self.forwarding_table
        )

        self.distance_vector = updated_distance_vector
        self.forwarding_table = updated_forwarding_table

        return routing_changed
    
    # Gửi distance vector đến hàng xóm (hoặc một hàng xóm cụ thể nếu target_port được chỉ định)
    def _broadcast_distance_vector(self, target_port=None):
            ports_to_send = (
                [target_port]
                if target_port is not None
                else list(self.neighbor_links.keys())
            )

            for port in ports_to_send:

                if port not in self.neighbor_links:
                    continue

                neighbor_address, _ = self.neighbor_links[port]

                advertised_routes = {}

                for destination, cost in self.distance_vector.items():
                    if destination == self.addr:
                        advertised_routes[destination] = cost
                        continue

                    if self.forwarding_table.get(destination) == port:
                        continue

                    advertised_routes[destination] = cost

                routing_packet = Packet(
                    kind=Packet.ROUTING,
                    src_addr=self.addr,
                    dst_addr=neighbor_address,
                    content=json.dumps(advertised_routes)
                )

                self.send(port, routing_packet)


    def handle_packet(self, port, packet):
        """Process incoming packet."""

        # Normal data packet
        if packet.is_traceroute:

            destination = packet.dst_addr

            if destination in self.forwarding_table:
                output_port = self.forwarding_table[destination]
                self.send(output_port, packet)

        else:

            neighbor_address = packet.src_addr

            received_distance_vector = json.loads(packet.content)
            if (
                self.received_distance_vectors.get(neighbor_address)
                == received_distance_vector
            ):
                return
            
            self.received_distance_vectors[
                neighbor_address
            ] = received_distance_vector

            routing_changed = self._recompute_routes()

            if routing_changed:
                self._broadcast_distance_vector()

    def handle_new_link(self, port, endpoint, cost):
        """Handle new link."""

        self.neighbor_links[port] = (endpoint, cost)

        if endpoint not in self.received_distance_vectors:
            self.received_distance_vectors[endpoint] = {}

        self._recompute_routes()
        self._broadcast_distance_vector()

    def handle_remove_link(self, port):
        """Handle removed link."""
        # TODO
        #   update the distance vector of this router
        #   update the forwarding table
        #   broadcast the distance vector of this router to neighbors
        pass

    def handle_time(self, time_ms):
        """Handle current time."""
        if time_ms - self.last_time >= self.heartbeat_time:
            self.last_time = time_ms
            # TODO
            #   broadcast the distance vector of this router to neighbors
            pass

    def __repr__(self):
        """Representation for debugging in the network visualizer."""
        # TODO
        #   NOTE This method is for your own convenience and will not be graded
        return f"DVrouter(addr={self.addr})"
