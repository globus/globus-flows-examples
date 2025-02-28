# Globus Compute and Transfer Flow Examples

This guide demonstrates how to build flows that combine Globus Compute and Globus Transfer to process and move data. You'll learn how to create two different flows that archive (tar) files and transfer them from a source collection to a destination collection.

## Prerequisites

Before starting, ensure you have a shared GCS collection and Globus Compute endpoint.
If you haven't set these up, follow [this guide](https://docs.globus.org/globus-connect-server/v5.4/) for setting up the GCS collection, and [this guide](https://globus-compute.readthedocs.io/en/latest/endpoints/installation.html) for setting up the Globus Compute endpoint. **Note**: The GCS collection and Globus Compute endpoint must have access to the same filesystem at the same path.

## Register the Globus Compute Function

First, register the `do_tar` Compute function that your flows will invoke to create the output tarfiles. Run the provided python script:

```bash
./transfer_compute_example/register_compute_func.py
```

and copy down the Compute function's UUID.

**Important**: Use the same Python version for registration as the one running on your Globus Compute Endpoint.

### The `do_tar` Compute function

`do_tar` takes four parameters that the flow will need to provide:

| Parameter | Description |
|-----------|-------------|
| `src_paths` | String or list of path(s) to files/directories to archive |
| `dest_path` | Where to write the tar.gz archive (directory or file path) |
| `transform_from` | The path prefix to replace (default: "/") |
| `transform_to` | The prefix to use for absolute paths (default: "/") |

### Path Transformation Explained

The parameters `transform_from` and `transform_to` handle differences between paths as exposed by the GCS collection and paths on the underlying filesystem.

**Example scenario:**
- Your GCS collection maps its root to the absolute path `/path/to/root/`.
- A user wants to tar the files at the absolute path `/path/to/root/input_files/`.
- To both the user and Flows service, this path appears as `/input_files/` on the GCS collection.
- However, the Compute function running on the GCS collection **does not know** about the mapping and can only find the files with the absolute paths.

Thus, the Compute function must be provided with the GCS root mapping to do any needed transformations. In this example:
- Set `transform_to` to the mapped root path (`/path/to/root/`) to transform the input `src_paths` to absolute paths.
- Set `transform_from` to the root directory (`/`) to transform the absolute paths to Globus paths.

These transformations ensure the Compute function can correctly locate and access files regardless of how collection paths are mapped.

## Compute and Transfer Flow: Example 1
In the first example, the Compute and Transfer flow takes a user-provided source file that already exists in the co-located GCS collection, creates a tarfile from it, and transfers the tarfile to a user provided destination collection. Specifically, the flow will:
1. Set constants for the run
2. Create an output directory named after the flow's run ID on your GCS collection
3. Invoke the Compute function `do_tar` on the source file and create a tarfile in the output directory
4. Transfer the resulting tarfile to the destination collection provided in the flow input
5. Delete the output directory

### Registering the Flow

1. Edit `compute_transfer_examples/compute_transfer_example_1_definition.json` and replace the placeholder values:
   - `gcs_endpoint_id`: Your GCS Collection ID
   - `compute_endpoint_id`: Your Compute Endpoint ID
   - `compute_func_id`: The UUID of the registered `do_tar` function
   - `compute_transform_from` and `compute_transform_to`: If your GCS collection uses path mapping

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
       "source_path": "/path/to/your/source/file",
       "destination_path": "/path/to/your/destination/file.tar.gz",
       "destination_endpoint_id": "your-destination-endpoint-uuid"
   }
   ```

2. Start the flow:
   ```bash
   globus flows start <FLOW_ID> \
     --input <YOUR FLOW INPUT FILE> \
     --label "Compute and Transfer Flow Example 1 Run"
   ```

3. Monitor the run progress:
   ```bash
   globus flows run show <RUN_ID>
   ```

## Compute and Transfer Flow: Example 2
In the second example, the Compute and Transfer flow takes in a user provided list source files that exists on a user provided source collection, creates a tarfile from it, and transfers the tarfile to a user provided destination collection. Specifically, the flow will:
1. Set constants for the run
2. Create an output directory named after the flow's run ID on your GCS collection
3. Iterate through the list of input source files and create the destination paths for files on your GCS collection
4. Transfer the source paths from the user-provided source collection to the newly created output directory folder on your GCS collection
5. Invoke the Compute function `do_tar` on the source files and create a tarfile in the output directory
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

3. Monitor the run progress:
   ```bash
   globus flows run show <RUN_ID>
   ```
