
mesh_folder="$1"
SDFGen="$2"
find ${mesh_folder} -name "*.obj" -type f | sort | awk 'NR >= 1 && NR <= 50000' | xargs -I{} -P 8 bash -c '
  # Print the filename and full path
  echo "Processing file: {}"

  # Get the full path of the file
  full_path=$(realpath "{}")

  # Check if corresponding .sdf file exists
  sdf_file="${full_path%.obj}.sdf"
  if [ -f "$sdf_file" ]; then
    echo "Skipping file: {} (corresponding .sdf file exists)"
    exit
  fi

  ${SDFGen} "$full_path" 0.04 5
'
