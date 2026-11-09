# Plain-guidance controlled rerun — kết quả

Plain-guidance rerun phát hiện **71/1454 eligible PUTs**, gồm56wrong-value và15resource;27/157eligible tasks có detection. Direct cũ77/1454 gồm61wrong-value,1exception và15resource. Chưa thấy thêm Plain cue giúp phục hồi baseline77;không suy ra cơ chế causal từ một generation mới.

Runtime gốc và164publicpackets được pin đúng bytes từ Direct77;giữ visibility/commonprompt,cap2048tokens/call,context8192,temp.7,seeds,inputbudget20 và native timeout8s. Thay đổi request là thêm câu Plain guidance;modelservedalias cùngQwen27 nhưng không có weights-hash của các server để chứng minh bit-identicalbackend.

Yield2909novel valid inputs;157/157generation responses,0unknown. Known tokens400272(prompt296917+completion103355). Full164records/157eligible/1454base-pass PUTs;7taskskiptheocohort.Scorerconfirm_first_failures,correctedreference2runs,inputfreeze,sourceguard vàimmutable replayPASS. Không import oldresponses/oracles vào generation mới.

Run đãCompleted. Report này chỉ đọc artifacts,0newmodel/nativecalls.

Prefect:http://127.0.0.1:4200/runs/flow-run/f539f740-d5b6-4978-a612-89ba37d4c1ab
