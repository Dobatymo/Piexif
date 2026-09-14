# Possible features

Ideas for future evaluation, not implemented behavior or commitments.

## Round-trip nonconforming camera metadata

Allow `dump()` to serialize safely parsed `load()` results from cameras that
write metadata which does not follow the EXIF specification. This would let
applications edit other tags without first repairing every nonconforming field.

- Motivating issue: [hMatoba/Piexif#83](https://github.com/hMatoba/Piexif/issues/83),
  whose sample stores `ComponentsConfiguration` as `BYTE` instead of `UNDEFINED`.
- Consider an explicit compatibility option that preserves original field types
  and values. The current value dictionaries do not retain each field's stored
  type, so preserving that information needs an API design decision.
- Distinguish preserving nonconforming data from normalizing it to valid EXIF;
  converting values to text is not a substitute for either operation.
- Retain bounds checks and reject truncated data and unsafe lengths or offsets.
  Supporting nonconforming tag types would not imply arbitrary corrupt-input
  recovery or byte-identical file round trips.

## Partial recovery of damaged EXIF

Offer an explicit tolerant loading mode that extracts safely readable metadata
when another field or IFD is damaged. This is separate from round-tripping
safely parsed but nonconforming camera metadata.

- Motivating issue: [hMatoba/Piexif#129](https://github.com/hMatoba/Piexif/issues/129),
  which reports an unreadable Interop IFD entry count.
- Report incomplete parsing and identify skipped fields or IFDs, rather than
  silently presenting unreadable metadata as absent.
- Keep strict loading as the default and retain bounds checks. Recovery must
  not follow invalid offsets or guess where missing structures belong.
- Partial results cannot preserve unreadable metadata when dumped. Make this
  limitation explicit so callers can choose whether to save the recovered data.
