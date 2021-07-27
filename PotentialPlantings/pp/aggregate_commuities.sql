WITH Community_Stats AS
(
	SELECT community, count(*) AS trees
	FROM sde.PP_TEST_PLANTS_PUBLISH
	GROUP BY community
)

SELECT communities.*, Community_Stats.trees
FROM sde.PP_TEST_MUNICOMMUNITYAREA_PROJECTED AS communities
JOIN Community_Stats ON Community_Stats.community = communities.community