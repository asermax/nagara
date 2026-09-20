"""The item pipeline: one ordered list of steps, positioned by item state.

``pipeline.advance(item, db)`` is the single entry the background task and the poll both
call. The queued phase (source, spawn, promote) is driven by the mortal in-process task;
the generating phase (extraction resolve, describe, synthesize, tts resolve, store) is
driven by poll, which is also the order a completing item moves through them in one
advance. Which steps run is a pure function of the item's status and row, so enqueue,
retry, and poll are the same advance entered at different points.
"""

from ..tts import ModalSynthesizer
from .context import PipelineContext
from .runner import Pipeline, PipelineStep
from .steps import (
    DescribeStep,
    ExtractionResolveStep,
    PromoteStep,
    ResolveStep,
    SourceStep,
    SpawnStep,
    StoreStep,
    SynthesizeStep,
)

_synthesizer = ModalSynthesizer()

pipeline = Pipeline(
    [
        SourceStep(),
        SpawnStep(),
        PromoteStep(),
        ExtractionResolveStep(),
        DescribeStep(),
        SynthesizeStep(_synthesizer),
        ResolveStep(_synthesizer),
        StoreStep(),
    ]
)

__all__ = ["Pipeline", "PipelineStep", "PipelineContext", "pipeline"]
