"""The item pipeline: one ordered list of steps, positioned by item state.

``pipeline.advance(item, db)`` is the single entry the background task (queued phase) and the
poll (generating phase) both call. Which steps run is a pure function of the item's status and
row, so enqueue, retry, and poll are the same advance entered at different points.
"""

from ..tts import ModalSynthesizer
from .context import PipelineContext
from .runner import Pipeline, PipelineStep
from .steps import (
    DescribeStep,
    ImageStep,
    ResolveStep,
    SourceStep,
    StoreStep,
    SynthesizeStep,
)

_synthesizer = ModalSynthesizer()

pipeline = Pipeline(
    [
        SourceStep(),
        ImageStep(),
        DescribeStep(),
        SynthesizeStep(_synthesizer),
        ResolveStep(_synthesizer),
        StoreStep(),
    ]
)

__all__ = ["Pipeline", "PipelineStep", "PipelineContext", "pipeline"]
