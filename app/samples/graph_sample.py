# -*- coding: utf-8 -*-


from app.model.SimpleSimulator import *
from app.entity.Entity import *
from app.tools.Convertor import Value


class SimpleEntity(Entity):

    def volume(self):
        return Value(self.capacity, "tM")

    def cost_pv(self):
        return {"capex": Value(self.capex, "$"), "opex": Value(self.opex, "$/tM") * self.volume()}

if __name__ == '__main__':
    e_sph = SimpleEntity("SPH", 1, 1, 1)
    n_sph = Node(e_sph)
    e_jph = SimpleEntity("JPH", 1, 1, 1)
    n_jph = Node(e_jph)
    l_chimie = Layer("Chemicals")
    for n in [n_sph, n_jph]:
        l_chimie.add_node(n)

    e_ywp = SimpleEntity("YoussoufiaWP", 1, 1, 1)
    n_ywp = Node(e_ywp)
    pipe = Transport({"type": "Pipe", "cost": 1, "unit": "$/T"}, 1)
    n_ywp.add_downstream(pipe, "SPH")
    n_ywp.add_downstream(pipe, "JPH")
    e_bgwp = SimpleEntity("BenGuerirWP", 1, 1, 1)
    n_bgwp = Node(e_bgwp)
    n_bgwp.add_downstream(pipe, "JPH")
    e_kwp = SimpleEntity("KhouribgaWP", 1, 1, 1)
    n_kwp = Node(e_kwp)
    n_kwp.add_downstream(pipe, "SPH")
    n_kwp.add_downstream(pipe, "JPH")
    l_wp = Layer("WashPlants")
    for n in [n_ywp, n_bgwp, n_kwp]:
        l_wp.add_node(n)

    e_km = SimpleEntity("KhouribgaMine", 1, 1, 1)
    n_km = Node(e_km)
    n_km.add_downstream(pipe, "KhouribgaWP")
    n_km.add_downstream(pipe, "YoussoufiaWP")
    e_bgm = SimpleEntity("BenGuerirMine", 1, 1, 1)
    n_bgm = Node(e_bgm)
    n_bgm.add_downstream(pipe, "YoussoufiaWP")
    n_bgm.add_downstream(pipe, "BenGuerirWP")
    e_ym = SimpleEntity("YoussoufiaMine", 1, 1, 1)
    n_ym = Node(e_ym)
    n_ym.add_downstream(pipe, "YoussoufiaWP")
    l_mine = Layer("Mines")
    for n in [n_km, n_bgm, n_ym]:
        l_mine.add_node(n)

    e_moon = SimpleEntity("Moon", 1, 1, 1)
    n_moon = Node(e_moon)
    l_moon = Layer("Moon")
    n_moon.add_downstream(pipe, "KhouribgaMine")
    n_moon.add_downstream(pipe, "BenGuerirMine")
    n_moon.add_downstream(pipe, "YoussoufiaMine")
    l_moon.add_node(n_moon)

    network = Network("NorthCenter")
    for l in [l_moon, l_mine, l_wp, l_chimie]:
        for l_name in l.nodes:
            for n in l.nodes[l_name]:
                network.add_node(n)

    g = Graph(network)
    g.apply_function("Moon", "SPH", "cost_pv")
    g.plot()

    s = SimpleSimulator(g)
    s.build_all_scenarios(["Moon"], ["JPH", "SPH"])
