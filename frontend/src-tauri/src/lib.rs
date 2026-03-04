// Learn more about Tauri commands at https://tauri.app/develop/calling-rust/
use std::fs::OpenOptions;
use std::io::Write;
use std::path::PathBuf;
use tauri::Manager;
use tauri_plugin_shell::process::CommandChild;
use tauri_plugin_shell::ShellExt;

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

struct BackendProcess(std::sync::Mutex<Option<CommandChild>>);

fn kill_backend(handle: &tauri::AppHandle) {
    if let Some(state) = handle.try_state::<BackendProcess>() {
        if let Ok(mut guard) = state.0.lock() {
            if let Some(child) = guard.take() {
                let _ = child.kill();
            }
        }
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let context = tauri::generate_context!();
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            let exe_dir: Option<PathBuf> = std::env::current_exe()
                .ok()
                .and_then(|p| p.parent().map(|d| d.to_path_buf()));

            let mut data_dir = exe_dir
                .map(|d| d.join("HK_Tauri_Data"))
                .unwrap_or_else(|| PathBuf::from(".").join("HK_Tauri_Data"));

            if std::fs::create_dir_all(&data_dir).is_err() {
                data_dir = app.path().app_data_dir()?.join("HK_Tauri_Data");
                std::fs::create_dir_all(&data_dir)?;
            }

            let log_path = data_dir.join("backend.log");

            let data_dir_str = data_dir.to_string_lossy().to_string();
            let parent_pid = std::process::id().to_string();
            let command = app
                .shell()
                .sidecar("backend")?
                .env("HK_TAURI_DATA_DIR", data_dir_str.clone())
                .env("HK_TAURI_CONFIG_DIR", data_dir_str)
                .env("HK_TAURI_PARENT_PID", parent_pid);

            let (mut rx, child): (_, CommandChild) = command.spawn()?;
            tauri::async_runtime::spawn(async move {
                let mut file = OpenOptions::new()
                    .create(true)
                    .append(true)
                    .open(log_path)
                    .ok();

                while let Some(event) = rx.recv().await {
                    if let Some(f) = file.as_mut() {
                        let _ = writeln!(f, "{:?}", event);
                    }
                }
            });

            app.manage(BackendProcess(std::sync::Mutex::new(Some(child))));
            Ok(())
        })
        .on_window_event(|window, event| {
            if matches!(event, tauri::WindowEvent::CloseRequested { .. }) {
                kill_backend(&window.app_handle());
            }
        })
        .invoke_handler(tauri::generate_handler![greet])
        .build(context)
        .expect("error while building tauri application");

    app.run(|app_handle, event| {
        if matches!(event, tauri::RunEvent::ExitRequested { .. } | tauri::RunEvent::Exit) {
            kill_backend(app_handle);
        }
    });
}
