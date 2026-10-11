import { ITEM_STATUS, type ItemRow, type Unit } from "@nagara/common";

const toUnitResponse = ({ spoken: _spoken, ...unit }: Unit, index: number) => ({
  index,
  ...unit,
});

export const toItemResponse = (row: ItemRow) => {
  const ready = row.status === ITEM_STATUS.ready;

  return {
    id: row.id,
    url: row.url,
    title: row.title,
    status: row.status,
    voice: row.voice,
    created_at: row.created_at,
    duration: ready ? row.duration : null,
    units: ready ? (row.units?.map(toUnitResponse) ?? null) : null,
    error: row.error,
    audio_url: ready ? `/items/${row.id}/audio` : null,
  };
};
