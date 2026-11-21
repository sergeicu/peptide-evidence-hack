"""Offline tests: every client parses its fixture and classifies correctly."""
import os
os.environ["PEPHACK_OFFLINE"] = "1"

from pephack import compounds, concentration, ctgov, europepmc, openfda, opentargets, pubmed


def test_registry_has_controls():
    cs = compounds.load()
    assert len(cs) >= 20
    statuses = {c.status_hypothesis for c in cs}
    # the controls are the point: without them you cannot detect an agent
    # that answers "no evidence" to everything
    assert "approved" in statuses
    assert "failed" in statuses
    assert sum(1 for c in cs if c.is_control) >= 5


def test_registry_lookup_by_alias():
    assert compounds.by_name("Ozempic").name == "Semaglutide"
    assert compounds.by_name("bpc-157").name == "BPC-157"


def test_mesh_classification():
    papers = pubmed.fetch(pubmed.search("x"))
    by_pmid = {p.pmid: p for p in papers}

    rodent = by_pmid["22300085"].classify()
    assert rodent["species"] == "animal"
    assert rodent["in_humans"] is False

    trial = by_pmid["19253699"].classify()
    assert trial["species"] == "human"
    assert trial["in_humans"] is True
    assert trial["design"] == "Randomized Controlled Trial"
    assert trial["is_trial"] is True

    # no MeSH at all must not be silently called 'animal'
    unindexed = by_pmid["31056810"].classify()
    assert unindexed["species"] == "unknown"
    assert unindexed["indexed_with_mesh"] is False
    assert unindexed["design"] == "Case Reports"


def test_paper_fields_parsed():
    papers = {p.pmid: p for p in pubmed.fetch(pubmed.search("x"))}
    p = papers["22300085"]
    assert p.year == 2012
    assert p.doi == "10.1000/example.2012.001"
    assert p.authors == ["Example A", "Second B"]
    assert any("Zagreb" in a for a in p.affiliations)
    # MedlineDate form ("2019 Apr-Jun") must still yield a year
    assert papers["31056810"].year == 2019


def test_concentration_detects_single_group():
    papers = pubmed.fetch(pubmed.search("x"))
    # 'Example A' appears on 2 of 3 fixture papers
    m = concentration.author_concentration(papers)
    assert m["top_author"] == "Example A"
    assert m["top_author_share"] > 0.6
    assert m["share_independent_of_top_author"] < 0.4
    assert "concentrated" in concentration.verdict({**m, "n_papers": 10})


def test_affiliation_clustering_groups_same_institution():
    affs = [
        "Department of Pharmacology, University of Zagreb School of Medicine, Zagreb, Croatia",
        "Department of Pharmacology, University of Zagreb School of Medicine, Zagreb, Croatia",
        "Clinical Trials Unit, Example Hospital, Boston, MA, USA",
    ]
    clusters = concentration.cluster_affiliations(affs)
    assert len(clusters) == 2
    assert max(clusters.values()) == 2


def test_ctgov_summary_counts_results_not_registrations():
    s = ctgov.summarise(ctgov.search("x"))
    assert s["registered"] == 2
    assert s["completed"] == 1
    # registration is not evidence: only one of two has posted anything
    assert s["with_posted_results"] == 1


def test_openfda_summary_carries_caveats():
    s = openfda.summarise("EXAMPLE PEPTIDE")
    assert s["faers_reports"] == 4
    assert s["has_fda_label"] is False
    assert any("not confirmed causal" in n for n in s["interpretation_notes"])


def test_opentargets_splits_evidence_by_datatype():
    res = opentargets.human_genetic_support("VEGFA")
    assert res["resolved"] is True
    assert res["any_genetic_support"] is True
    rows = {r["disease"]: r for r in res["rows"]}
    wound = rows["example wound healing condition"]
    # animal-model-driven association must not look like human genetic support
    assert wound["genetic_association"] == 0.0
    assert wound["driven_by"] == "animal_model"


def test_europepmc_fixtures():
    assert europepmc.hit_count("x") == 2
    assert len(europepmc.citations("22300085")) == 1
    assert len(europepmc.references("22300085")) == 1
    rec = europepmc.search("x")[0]
    names = [n for n, _ in europepmc.iter_authors(rec)]
    assert names == ["Example A"]
