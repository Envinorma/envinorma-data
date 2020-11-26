from lib.topics.patterns import Topic, TopicName, TopicOntology, normalize, parse, tokenize, detect_matched_patterns


def test_detect_matched_patterns():
    topic_eau = Topic.from_raw_patterns(TopicName.EAU, [], ["Eau"], ["Collecte et rejet des effluents"])
    topic_dechets = Topic.from_raw_patterns(
        TopicName.DECHETS, [], ["Déchets", 'DêcheT'], ["Collecte et recyclage des déchets"]
    )
    ontology = TopicOntology([topic_eau, topic_dechets])
    assert detect_matched_patterns(ontology, 'il y a de l\'eau', TopicName.EAU) == set()
    assert detect_matched_patterns(ontology, 'il y a de l\'eau', TopicName.EAU, True) == {'eau'}
    assert detect_matched_patterns(ontology, 'il y a de l\'eau et des déchets.', TopicName.EAU, True) == {'eau'}
    assert detect_matched_patterns(ontology, 'il y a de l\'eau et des déchets.', TopicName.DECHETS, True) == {
        'dechets'
    }  # TODO!
    assert detect_matched_patterns(ontology, 'il y a de l\'eau et des déchets.', None, True) == {
        'dechets',
        'eau',
    }  # TODO!


def test_parse():
    topic = Topic.from_raw_patterns(TopicName.EAU, [], ["Eau"], ["Collecte et rejet des effluents"])
    ontology = TopicOntology([topic])
    assert parse(ontology, 'il y a de l\'eau') == set()
    assert parse(ontology, 'il y a de l\'eau', True) == {TopicName.EAU}
    assert parse(ontology, 'il y a de l\'eau dans la collecte et rejet des effluents.') == {TopicName.EAU}


def test_parse_2():
    topic_eau = Topic.from_raw_patterns(TopicName.EAU, [], ["Eau"], ["Collecte et rejet des effluents"])
    topic_dechets = Topic.from_raw_patterns(
        TopicName.DECHETS, [], ["Déchets", 'DêcheT'], ["Collecte et recyclage des déchets"]
    )
    ontology = TopicOntology([topic_eau, topic_dechets])
    assert parse(ontology, 'il y a de l\'eau et des déchets.') == set()
    assert parse(ontology, 'il y a de l\'eau et des déchets.', True) == {TopicName.EAU, TopicName.DECHETS}
    assert parse(ontology, 'il y a un dechet dans la collecte et rejet des effluents.', True) == {
        TopicName.EAU,
        TopicName.DECHETS,
    }


def test_tokenize():
    assert tokenize('Foo bar foo') == ['Foo', 'bar', 'foo']
    assert tokenize('Foo bar  foo') == ['Foo', 'bar', 'foo']
    assert tokenize('Foo bar---foo') == ['Foo', 'bar', 'foo']
    assert tokenize('Foo\'bar:foo') == ['Foo', 'bar', 'foo']


def test_normalize():
    assert normalize('Ce sont: des   déchets banals.') == 'ce sont des dechets banals '

    expected = 'il sollicite en tout etat de cause l avis du conseil departemental'
    assert normalize('il sollicite en tout état de cause l\'avis du conseil départemental') == expected

    expected = 'de l environnement et des risques sanitaires et technologiques'
    assert normalize('de l\'environnement et des risques sanitaires et technologiques') == expected

    assert normalize('sur le projet d\'arrêté d\'autorisation') == 'sur le projet d arrete d autorisation'
