# Ai-Transcriber

<details>
<summary><h2>Architecture</h2></summary>

### System Context

![System Context](.assets/index.png)

### Containers - Diarizer

The API accepts an upload and returns. Worker consumes the job out of band. Redis carries the job and its result.

![Containers - Diarizer](.assets/diarizerContainers.png)

### Components - Diarizer API

![Components - Diarizer API](.assets/diarizerApiComponents.png)

### Components - Diarization Worker

![Components - Diarization Worker](.assets/diarizerWorkerComponents.png)

### Flow - Diarize an audio file

![Flow - Diarize an audio file](.assets/diarizeFlow.png)

</details>