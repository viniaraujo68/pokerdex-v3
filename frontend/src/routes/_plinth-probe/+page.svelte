<script>
	import { Logo } from '@viniaraujo68/plinth/components';

	const themes = ['plinth-light', 'plinth-dark'];
</script>

<div class="flex flex-col gap-6 p-6">
	<h2 class="text-lg font-semibold">plinth foundation probe</h2>

	{#each themes as theme (theme)}
		<div
			data-theme={theme}
			class="rounded-box bg-base-100 text-base-content flex flex-col gap-4 border border-current/15 p-4"
		>
			<span class="text-sm opacity-70">data-theme="{theme}"</span>

			<div class="flex flex-wrap items-center gap-4">
				<Logo class="text-3xl" />
				<span class="badge badge-soft badge-success">success</span>
				<span class="badge badge-soft badge-error">error</span>
				<kbd class="kbd">⌘K</kbd>
				<input class="input" value="input" />
				<select class="select w-40">
					<option>select</option>
				</select>
			</div>

			<div class="alert alert-info">daisyUI alert on plinth tokens</div>

			<progress class="progress progress-primary w-56" value="40" max="100"></progress>

			<table class="table">
				<thead>
					<tr><th>Column</th><th>Value</th></tr>
				</thead>
				<tbody>
					<tr><td>plinth table</td><td class="font-mono">1234</td></tr>
				</tbody>
			</table>
		</div>
	{/each}
</div>
