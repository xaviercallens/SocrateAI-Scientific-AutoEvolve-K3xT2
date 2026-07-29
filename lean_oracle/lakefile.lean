import Lake
open Lake DSL

package «lean_oracle» where
  -- Package configuration options

@[default_target]
lean_exe «rpc_server» where
  root := `rpc_server

lean_lib «GeneratedK3» where
  roots := #[`GeneratedK3]

