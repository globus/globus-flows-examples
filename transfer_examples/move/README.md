# Move (copy and delete) files

## Description

Perform a "move" operation on a directory by first transferring from a source to a destination and then deleting from the source.
The entire directory's contents, including files and subdirectories, will be copied to the destination and then deleted from the source.

> [!NOTE]
> This example differs from the
> [Move (copy and delete) files](https://app.globus.org/flows/f37e5766-7b3c-4c02-92ee-e6aacd8f4cb8/definition)
> Globus-provided Flow available in the Globus Web App.
>
> It is simplified and may exhibit slightly different behaviors.

## Highlights

In the example definition, the `IdentifyPathTypes` state uses expression evaluators to prepare several boolean values.

These boolean values are used by the `TestPathConstraints` state to conditionally modify the destination path used by the `Transfer` state.
