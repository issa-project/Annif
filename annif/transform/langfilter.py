"""Transformation filtering out parts of a text that are in a language
different from the language of the project."""

import annif
from . import transform

logger = annif.logger


class LangFilter(transform.BaseTransform):

    name = 'filter_lang'

    def __init__(self, project, text_min_length=500, sentence_min_length=50):
        super().__init__(project)
        self.text_min_length = int(text_min_length)
        self.sentence_min_length = int(sentence_min_length)

    def transform_fn(self, text):
        if len(text) < self.text_min_length:
            return text

        retained_sentences = []
        sentences = self.project.analyzer.tokenize_sentences(text)
        for sent in sentences:
            if len(sent) < self.sentence_min_length:
                retained_sentences.append(sent)
                continue
            detected_lang, probability = annif.util.detect_language(sent)
            if detected_lang == self.project.language or detected_lang is None:
                retained_sentences.append(sent)
        text_out = ' '.join(retained_sentences)
        return text_out
