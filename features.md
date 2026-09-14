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
