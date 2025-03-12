# Globus Compute and Transfer Flow Examples

This guide demonstrates how to build flows that combine Globus Compute and Globus Transfer to process and move data. You'll learn how to create two different flows that archive (tar) files and transfer them from a source collection to a destination collection.

## Prerequisites

Before starting, ensure you have a shared GCS collection and Globus Compute endpoint.
If you haven't set these up, follow [this guide](https://docs.globus.org/globus-connect-server/v5.4/) for setting up the GCS collection, and [this guide](https://globus-compute.readthedocs.io/en/latest/endpoints/installation.html) for setting up the Globus Compute endpoint. **Note**: The GCS collection and Globus Compute endpoint must both have read/write permissions to the same filesystem location where operations will be performed.

## Register the Globus Compute Function

First, register the `do_tar` Compute function that your flows will invoke to create the output tarfiles. Run the provided python script:

```bash
./transfer_compute_example/register_compute_func.py
```

and save the Compute function's UUID.

**Important**: Use the same Python version for registration as the one running on your Globus Compute Endpoint.

### The `do_tar` Compute function

`do_tar` takes three parameters that the flow will need to provide:

| Parameter | Description |
|-----------|-------------|
| `src_paths` | List of paths to the files/directories to be archived |
| `dest_path` | Where to write the tar archive (directory or file path) |
| `gcs_base_path` | The shared GCS collection's configured base path. (default: "/") |

### GCS Collection Base Paths

The parameter `gcs_base_path` is provided to the compute function to allow it to transform the user input paths to absolute paths. This is needed when the shared GCS instance has [configured the collection's base path](https://docs.globus.org/globus-connect-server/v5/data-access-guide/#configure_collection_base_path).

**Example scenario:**
- Your GCS collection has configured its base path to `/path/to/root/`.
- A user wants to tar the files at the absolute path `/path/to/root/input_files/`.
- To both the user and Flows service, this path appears as `/input_files/` on the GCS collection.
- However, the Compute function running on the shared GCS instance **does not know** about the collection's configured base path and can only find the files using absolute paths.

Thus, the Compute function must be provided with the GCS collection's configured base path to do the necessary transformations. In this example, `gcs_base_path` would need to be set to `/path/to/root/`.

## Compute and Transfer Flow: Example 1
In the first example, the Compute and Transfer flow takes a user-provided list of source files that **already** exists in the co-located GCS collection, creates a tarfile from them, and transfers the tarfile to a user-provided destination collection. Specifically, the flow will:
1. Set constants for the run
2. Create an output directory named after the flow's run ID on your GCS collection
3. Invoke the Compute function `do_tar` on the source endpoint to create a tar archive from the input source files and save it in the output directory
4. Transfer the resulting tarfile to the destination collection provided in the flow input
5. Delete the output directory

### Registering the Flow

1. Edit `compute_transfer_examples/compute_transfer_example_1_definition.json` and replace the placeholder values:
   - `gcs_endpoint_id`: Your GCS Collection ID
   - `compute_endpoint_id`: Your Compute Endpoint ID
   - `compute_function_id`: The UUID of the registered `do_tar` function

If your GCS collection has a configured base path, also edit `gcs_base_path`.


2. Register the flow:
   ```bash
   globus flows create "Compute and Transfer Flow Example 1" \
     ./compute_transfer_examples/compute_transfer_example_1_definition.json \
     --input-schema ./compute_transfer_examples/compute_transfer_example_1_schema.json
   ```

3. Save the Flow ID returned by this command

### Running the Flow

1. Create the flow input json file like so:
   ```json
   {
       "source_paths": ["/path/to/file1", "/path/to/file2"],
       "destination_path": "/path/to/your/destination/file.tar.gz",
       "destination_endpoint_id": "your-destination-endpoint-uuid"
   }
   ```

2. Start the flow:
   ```bash
   globus flows start <YOUR FLOW ID> \
     --input <YOUR FLOW INPUT FILE> \
     --label "Compute and Transfer Flow Example 1 Run"
   ```
   And save the run ID for use in the next command.

3. Monitor the run progress:
   ```bash
   globus flows run show <RUN_ID>
   ```
   At this point, you might see that your flow has gone INACTIVE. This is because you need to give data access consents for any GCS collection that your flow is interacting with. Run the command:

   ```bash
   globus flows run resume <RUN_ID>
   ```
   And you will be prompted to run a `globus session consent`. After granting the requested consent, try resuming the run once again and your flow should be able to proceed. As your flow encounters more required data access consents, you might need to repeat this step multiple times, however once you have granted a consent, it will remain for all future runs of that flow.

## Compute and Transfer Flow: Example 2
In the second example, the Compute and Transfer flow takes in a user-provided list of source files that exist on a user-provided source collection, creates a tarfile from it, and transfers the tarfile to a user-provided destination collection. Specifically, the flow will:
1. Set constants for the run
2. Create an output directory named after the flow's run ID on your GCS collection
3. Iterate through the list of input source files and create the destination paths for files on your GCS collection
4. Transfer the source paths from the user-provided source collection to the newly created output directory folder on your GCS collection
5. Invoke the Compute function `do_tar` on the source endpoint to create a tar archive from the input source files and save it in the output directory
6. Transfer the resulting tarfile to the destination collection provided in the flow input
7. Delete the output directory

**Implementation Note**: Step 3 is implemented using six different states in the flow definition (`SetSourcePathsIteratorVariables`, `EvalShouldIterateSourcePaths`, `IterateSourcePaths`, `EvalGetSourcePath`, `GetSourcePathInfo`, and `EvalSourcePathInfo`). These states work together to create a loop that processes each source path. While this demonstrates how to implement an iteration in Flows, a simpler approach could be to create a separate Compute function to handle this work, which would significantly reduce the complexity of this flow.

### Registering the Flow

1. Edit `compute_transfer_examples/compute_transfer_example_2_definition.json` and replace the placeholder values (same as in the first example).

2. Register as a new flow:
   ```bash
   globus flows create "Compute and Transfer Flow Example 2" \
     ./compute_transfer_examples/compute_transfer_example_2_definition.json \
     --input-schema ./compute_transfer_examples/compute_transfer_example_2_schema.json
   ```

   Or update the existing flow from example 1:
   ```bash
   globus flows update <FLOW_ID> \
     --title "Compute and Transfer Flow Example 2" \
     --definition ./compute_transfer_examples/compute_transfer_example_2_definition.json \
     --input-schema ./compute_transfer_examples/compute_transfer_example_2_schema.json
   ```

3. Save the Flow ID returned by this command

### Running the Flow

1. Create the input json file for your flow:
   ```json
   {
       "source_endpoint": "your-source-endpoint-uuid",
       "source_paths": ["/path/to/file1", "/path/to/file2"],
       "destination": {
           "id": "your-destination-endpoint-uuid",
           "path": "/path/to/your/destination/archive.tar.gz"
       }
   }
   ```

2. Start the flow:
   ```bash
   globus flows start <FLOW_ID> \
     --input <YOUR FLOW INPUT FILE> \
     --label "Compute and Transfer Flow Example 2 Run"
   ```
   And save the run ID for use in the next command.

3. Monitor the run progress:
   ```bash
   globus flows run show <RUN_ID>
   ```

   Remember, if your flow has gone inactive, run:
   ```bash
   globus flows run resume <RUN_ID>
   ```
   and then run the prompted `globus session consent` command and try resuming the run again.