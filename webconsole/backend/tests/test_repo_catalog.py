from eovrt_webconsole.repo_catalog import get_prompt_set, list_experiments, list_prompt_sets


def test_list_prompt_sets_con_frozen(repo):
    sets = {s["id"]: s for s in list_prompt_sets(repo / "prompts", frozenset({"frozen_set"}))}
    assert set(sets) == {"demo_set", "frozen_set"}
    assert sets["frozen_set"]["frozen"] is True
    assert sets["demo_set"]["frozen"] is False
    assert [c["id"] for c in sets["demo_set"]["classes"]] == ["person", "helmet"]
    assert sets["demo_set"]["classes"][0]["phrasings"] == {"default": ["person"]}


def test_get_prompt_set_devuelve_dict_interno(repo):
    ps = get_prompt_set(repo / "prompts", "demo_set")
    assert ps["id"] == "demo_set"
    assert "classes" in ps  # shape de PromptSet (set_inline), sin la clave raíz prompt_set


def test_get_prompt_set_inexistente(repo):
    assert get_prompt_set(repo / "prompts", "nope") is None


def test_list_experiments_recursivo_con_grupos(repo):
    exps = {e["id"]: e for e in list_experiments(repo / "experiments")}
    assert set(exps) == {"demo_manifest", "bench_v2/bench_manifest"}
    assert exps["demo_manifest"]["group"] == ""
    assert exps["bench_v2/bench_manifest"]["group"] == "bench_v2"
    assert exps["demo_manifest"]["manifest"]["source"] == {"ref": "demo_v2"}


def test_endpoints_catalogo_in_repo(client):
    sets = client.get("/api/catalog/prompt-sets").json()
    assert {s["id"] for s in sets} == {"demo_set", "frozen_set"}
    exps = client.get("/api/catalog/experiments").json()
    assert {e["id"] for e in exps} == {"demo_manifest", "bench_v2/bench_manifest"}


def test_list_prompt_sets_expone_estrategia_y_condicion_de_cada_clase(tmp_path):
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    (prompts / "s.yaml").write_text(
        "prompt_set:\n"
        "  id: s\n"
        "  classes:\n"
        "    - {id: cr01_neg, strategy: syntactic_negation, condition_id: CR-01,\n"
        "       phrasings: {default: [person without hard hat]}}\n"
        "    - {id: person, phrasings: {default: [person]}}\n"
    )
    clases = {c["id"]: c for c in list_prompt_sets(prompts, frozenset())[0]["classes"]}
    # Con ellos la consola explica la clase al pasar el cursor, sin una tabla escrita a mano.
    assert clases["cr01_neg"]["strategy"] == "syntactic_negation"
    assert clases["cr01_neg"]["condition_id"] == "CR-01"
    # Una clase que no los declara no inventa nada.
    assert clases["person"]["strategy"] is None
    assert clases["person"]["condition_id"] is None
