# Source and runtime binding

The C2 run used the immutable source and image set below. The successful execution occurred before the later runtime-only stop fix; the stop fix was then deployed to perform the formal cancellation cleanup.

| Item | Binding |
| --- | --- |
| Worker/Platform source | `df5c926435c2c620bdbd33cd8d2a277440ff980b` |
| Runtime stop fix | `556b8f4bfa59ed9cdede9c3aa893212dc5c13c72` |
| Task | `2032601e-79ac-4e5d-bc5f-7a33620e3659` |
| Pod | `wuji-task-v-6c55a7ade961603dfaf6fa45d99c531d-a1` |
| Pod UID | `6db41752-9826-4687-aae4-b9cf5e640632` |
| Database | `wuji_vnext_c2_20260914_r6` |
| Agent image | `127.0.0.1:56615/wuji-vnext-agent@sha256:d771f77f8345bdbc95b7f29cd7f7074f7440e292fc2c8ca251cf610e3fc58cfb` |
| Kali image | `127.0.0.1:56615/wuji-vnext-kali@sha256:7a11a2b71e61a25ecc75de2556f793d71ac7123cb75e559b1d28a9c87f892011` |
| Platform image | `127.0.0.1:56615/wuji-vnext-platform@sha256:e98f5381230c055a8a478a50308d19e7481aea8c03286c1efbf9f6c4691a8bbd` |

The C2 run was performed through `PodEnvironment → VNextPodRuntime → TaskRuntimeController.ensure()`. The controller reread the real Pod UID and the database receiver row before Scheduler/Outbox dispatch. The two agent runs exited with real process observations and were accepted by P04. The later cancellation was performed through the Runtime command API; the receiver was disabled, capacity returned to zero, and the Task Pod was removed by the formal stop path.

A separate runtime image containing the stop fix was deployed afterward. This distinction is kept because a result must remain bound to the code that produced it.
