# P04 final scoped controller review

Main controller reviewed18d0332..01a7fe0, code2ce5250. F1/P1 andF2/P3: ADDRESSED. No new blocking issue found in this narrow change. This is controller source/evidence review, not an independent test run.

inputs_current uses a fixed-search-path SECURITY DEFINER boolean. It checks current scope/liveACL/readability of the exact referenced revision, then later domain versions without viewerRLS filtering. No hidden version/ID/count is returned. Fact retainsRR; ResultCommitter retainsTask-locked publication. All known migration paths add vnext_0005_p04_input_freshness; unknown sets reject.

Fresh checks: all4testedcode fingerprints match2ce5250; currentchangedcode matchescommit; diffcheckpasses; all19archivedevidence hashesmatch. For15non-HTTP entries, original/decompressed hashesandlengthsalso match. FourHTTPfiles explicitlyreplacefixtureAuthorization, so original_sha/bytes describe pre-redaction input, notarchivedbytes; recordedheaderfingerprints/subjects andbodyContent-Length were checked. An initial localverification mistakenlycomparedthose different representations, failed, andwas corrected withoutchangingevidence. RenamedJPEG is byte-identicalto18d0332.

Recorded finaltargeted result3passed/24deselected,1.64s covers high/lowFactafterprivatev2, actualResultCommitter STALE_INPUT andmigration/reapply. Original24/6resultskeeptheirSHAs, no rerun. P04 sliceaccepted; downstreamexecution/Goal/topologyremainfuture.
